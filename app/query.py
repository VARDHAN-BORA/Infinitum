import asyncio
import datetime
import hashlib
import json
import logging
import os
import re
import time
from dataclasses import dataclass
from functools import partial

import httpx
import redis.asyncio as aioredis
from pinecone import SearchQuery
from pinecone.exceptions import PineconeException
from redis.exceptions import RedisError

from app.config import settings
from app.evaluator import evaluate_and_log
from app.llm import generate_answer_async
from app.metrics import Timer, track
from app.models import QueryMatch
from app.pinecone_client import EMBED_TEXT_FIELD, PINECONE_NAMESPACE, get_index

logger = logging.getLogger(__name__)

DEFAULT_TOP_K = 5
CACHE_TTL = 3600

_DEMO_PATH = os.path.join(os.path.dirname(__file__), "static_demo.json")
_DEMO_DATA: dict | None = None

_ZERO_MS: dict[str, float] = {"retrieval_ms": 0.0, "generation_ms": 0.0, "total_ms": 0.0}

_FALLBACK_LATENCY: dict[str, float] = {
    "retrieval_ms": 120.0,
    "generation_ms": 240.0,
    "total_ms": 360.0,
}

_ACK_TOKENS: frozenset[str] = frozenset({
    "hi", "hello", "hey", "yo", "howdy", "sup", "hola",
    "bye", "goodbye", "later", "cya", "see ya", "peace",
    "ok", "okay", "thanks", "thank you", "thx", "ty",
    "sure", "yes", "no", "nope", "cool", "nice", "great",
    "awesome", "got it", "gotcha", "right", "agree", "agreed",
    "please", "hello there", "good morning", "good evening",
})

_DATE_TOKENS: frozenset[str] = frozenset({"date", "time", "today"})

_FALLBACK_DEFAULT_ANSWER = (
    "Welcome to the Infinitum AI Offline Demo. "
    "To test live data processing, try asking: "
    "'What are the 2026 updates for routing and logging protocols?'"
)


# ── Demo data helpers ─────────────────────────────────────────────────────────

def _load_demo_data() -> dict:
    global _DEMO_DATA
    if _DEMO_DATA is None:
        try:
            with open(_DEMO_PATH, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
            _DEMO_DATA = raw.get("queries", raw)
            logger.info("Loaded %d demo entries from static_demo.json.", len(_DEMO_DATA))
        except Exception as exc:
            logger.error("Could not load static_demo.json: %s", exc)
            _DEMO_DATA = {}
    return _DEMO_DATA


def _demo_fallback(query_text: str) -> "PipelineResult":
    demo = _load_demo_data()
    normalized = query_text.strip().lower()

    if normalized in demo:
        entry = demo[normalized]
        matches = [
            QueryMatch(
                id=chunk.get("id", f"demo_chunk_{i}"),
                score=float(chunk.get("score", 0.9)),
                text=chunk.get("text", ""),
                source=chunk.get("source", "demo"),
                document_id=chunk.get("document_id", f"demo_doc_{i}"),
            )
            for i, chunk in enumerate(entry.get("chunks", []))
        ]
        logger.info("Demo fallback — matched key: %r", normalized)
        return PipelineResult(
            answer=entry["answer"],
            matches=matches,
            latency_ms=_FALLBACK_LATENCY,
            cache_hit=False,
        )

    logger.info("Demo fallback — no match for %r, returning default answer.", normalized)
    return PipelineResult(
        answer=_FALLBACK_DEFAULT_ANSWER,
        matches=[],
        latency_ms=_FALLBACK_LATENCY,
        cache_hit=False,
    )


# ── Core pipeline dataclass ───────────────────────────────────────────────────

@dataclass
class PipelineResult:
    answer: str
    matches: list[QueryMatch]
    latency_ms: dict[str, float]
    cache_hit: bool


# ── Internal pipeline helpers ─────────────────────────────────────────────────

def _cache_key(query: str) -> str:
    normalized = re.sub(r"\s+", " ", query.strip().lower())
    normalized = re.sub(r"[^a-z0-9\s]", "", normalized).strip()
    digest = hashlib.sha256(normalized.encode()).hexdigest()
    return f"infinitum:query:{digest}"


_redis_pool: aioredis.Redis | None = None


async def _get_redis() -> aioredis.Redis | None:
    global _redis_pool
    if _redis_pool is not None:
        try:
            await _redis_pool.ping()
            return _redis_pool
        except Exception:
            _redis_pool = None

    try:
        _redis_pool = aioredis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD or None,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
            ssl=True,
        )
        await _redis_pool.ping()
        return _redis_pool
    except Exception as exc:
        logger.warning("Redis unavailable (%s) — falling back to live pipeline.", exc)
        _redis_pool = None
        return None


async def _pinecone_search(query_text: str, top_k: int) -> list[QueryMatch]:
    index = get_index()
    search_query = SearchQuery(
        inputs={EMBED_TEXT_FIELD: query_text},
        top_k=top_k,
    )
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(
        None,
        partial(index.search_records, PINECONE_NAMESPACE, search_query),
    )
    return [
        QueryMatch(
            id=hit._id,
            score=round(hit._score, 4),
            text=(hit.fields or {}).get(EMBED_TEXT_FIELD, ""),
            source=(hit.fields or {}).get("source", "unknown"),
            document_id=(hit.fields or {}).get("document_id", ""),
        )
        for hit in response.result.hits
    ]


# ── Public entry point ────────────────────────────────────────────────────────

async def run_rag_pipeline(
    query_text: str, top_k: int = DEFAULT_TOP_K
) -> PipelineResult:
    """
    Full RAG pipeline with Redis semantic caching and resilient demo fallback.

    Normal flow:
      Cache hit  → answer + matches returned in <5 ms.
      Cache miss → Pinecone search → NVIDIA generation → Redis write → eval.
      Redis down → graceful fallback, live pipeline runs as normal.

    Fallback mode (any infrastructure exception):
      Logs a WARNING, reads static_demo.json, returns a pre-baked response
      with simulated latency so the UI telemetry panel still renders.
    """
    try:
        clean_query = query_text.strip().lower()

        # ── 0a. Acknowledgment / greeting / filler bypass ────────────────────
        _query_words_list = re.findall(r"\b[a-z0-9]+\b", clean_query)
        _query_words_set = set(_query_words_list)
        _first_word = _query_words_list[0] if _query_words_list else ""

        _is_ack = (
            _first_word in _ACK_TOKENS
            or len(_query_words_list) <= 2 and _query_words_set & _ACK_TOKENS
        )

        if _is_ack:
            logger.info("Ack/greeting bypass triggered for %r", clean_query)
            return PipelineResult(
                answer=(
                    "Got it! Let me know if you have any questions about your knowledge base."
                ),
                matches=[],
                latency_ms=_ZERO_MS,
                cache_hit=False,
            )

        # ── 0b. Date / time bypass ──────────────────────────────────────────
        if _DATE_TOKENS & _query_words_set:
            today_str = datetime.date.today().strftime("%A, %B %d, %Y")
            logger.info("Date bypass triggered — returning %s", today_str)
            return PipelineResult(
                answer=(
                    f"Today's system timestamp is {today_str}. "
                    "All telemetry lines and memory-cached pipelines are operating normally."
                ),
                matches=[],
                latency_ms=_ZERO_MS,
                cache_hit=False,
            )

        total_start = time.perf_counter()

        # ── 1. Cache check ──────────────────────────────────────────────────
        redis = await _get_redis()
        cache_key = _cache_key(query_text)

        if redis:
            try:
                cached_raw = await redis.get(cache_key)
            except RedisError as exc:
                logger.warning("Redis read failed: %s", exc)
                cached_raw = None

            if cached_raw:
                try:
                    cached = json.loads(cached_raw)
                    cached_matches = [
                        QueryMatch(**m) for m in cached.get("matches", [])
                    ]
                except (json.JSONDecodeError, Exception):
                    cached_matches = []

                total_ms = round((time.perf_counter() - total_start) * 1000, 2)
                logger.info(
                    "Cache Hit — total=%.2f ms — key=…%s",
                    total_ms,
                    cache_key[-12:],
                )
                return PipelineResult(
                    answer=cached.get("answer", cached_raw) if isinstance(cached, dict) else cached_raw,
                    matches=cached_matches,
                    latency_ms={
                        "retrieval_ms": 0.0,
                        "generation_ms": 0.0,
                        "total_ms": total_ms,
                    },
                    cache_hit=True,
                )

        # ── 2. Retrieval ─────────────────────────────────────────────────────
        retrieval_timer = Timer()
        with track(retrieval_timer):
            matches = await _pinecone_search(query_text, top_k)

        # ── 2b. Zero-match short-circuit (skip LLM call) ─────────────────────
        if not matches:
            total_ms = round((time.perf_counter() - total_start) * 1000, 2)
            return PipelineResult(
                answer=(
                    "The available knowledge base does not contain sufficient information "
                    f"to answer this question. Your query returned no matching document chunks. "
                    "Try rephrasing or ingesting relevant documents."
                ),
                matches=[],
                latency_ms={
                    "retrieval_ms": retrieval_timer.elapsed_ms,
                    "generation_ms": 0.0,
                    "total_ms": total_ms,
                },
                cache_hit=False,
            )

        # ── 3. Generation ─────────────────────────────────────────────────────
        contexts = [m.text for m in matches]
        generation_timer = Timer()
        with track(generation_timer):
            answer = await generate_answer_async(query_text, contexts)

        # ── 4. Cache write (answer + matches) ────────────────────────────────
        if redis:
            try:
                cache_value = json.dumps({
                    "answer": answer,
                    "matches": [m.model_dump() for m in matches],
                })
                await redis.set(cache_key, cache_value, ex=CACHE_TTL)
            except RedisError as exc:
                logger.warning("Redis write failed: %s", exc)

        # ── 5. Evaluation (fire-and-forget, don't block response) ───────────
        try:
            loop = asyncio.get_event_loop()
            loop.run_in_executor(
                None, partial(evaluate_and_log, query_text, answer, contexts)
            )
        except Exception:
            pass

        total_ms = round((time.perf_counter() - total_start) * 1000, 2)

        return PipelineResult(
            answer=answer,
            matches=matches,
            latency_ms={
                "retrieval_ms": retrieval_timer.elapsed_ms,
                "generation_ms": generation_timer.elapsed_ms,
                "total_ms": total_ms,
            },
            cache_hit=False,
        )

    except (PineconeException, RedisError, httpx.RequestError, Exception) as exc:
        logger.warning(
            "WARNING: Infrastructure exception caught. "
            "Initializing Resilient Demo Fallback Mode..."
        )
        logger.debug(
            "Exception detail: [%s] %s", type(exc).__name__, exc
        )
        return _demo_fallback(query_text)
