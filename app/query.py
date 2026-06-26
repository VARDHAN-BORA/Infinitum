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
from app.pinecone_client import EMBED_TEXT_FIELD, PINECONE_NAMESPACE
from app.pinecone_client import index as _index

logger = logging.getLogger(__name__)

DEFAULT_TOP_K = 5
CACHE_TTL = 3600  # 1 hour

# Resolved once at module load — works regardless of the process working directory.
_DEMO_PATH = os.path.join(os.path.dirname(__file__), "static_demo.json")
_DEMO_DATA: dict | None = None

_ZERO_MS: dict[str, float] = {"retrieval_ms": 0.0, "generation_ms": 0.0, "total_ms": 0.0}

_FALLBACK_LATENCY: dict[str, float] = {
    "retrieval_ms": 120.0,
    "generation_ms": 240.0,
    "total_ms": 360.0,
}

_GREETING_TOKENS: frozenset[str] = frozenset({"hi", "hello", "hey", "yo"})
_DATE_TOKENS: frozenset[str] = frozenset({"date", "time", "today"})
_FALLBACK_DEFAULT_ANSWER = (
    "Welcome to the Infinitum AI Offline Demo. "
    "To test live data processing, try asking: "
    "'What are the 2026 updates for routing and logging protocols?'"
)


# ── Demo data helpers ─────────────────────────────────────────────────────────

def _load_demo_data() -> dict:
    """
    Load static_demo.json once and cache the inner 'queries' dict in memory.

    The JSON schema wraps entries under a top-level "queries" key:
        { "queries": { "<normalized query>": { "answer": ..., "chunks": [...] } } }
    We unwrap that here so callers get a flat {query: entry} dict.
    """
    global _DEMO_DATA
    if _DEMO_DATA is None:
        try:
            with open(_DEMO_PATH, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
            # Support both the wrapped {"queries": {...}} schema and a flat schema.
            _DEMO_DATA = raw.get("queries", raw)
            logger.info("Loaded %d demo entries from static_demo.json.", len(_DEMO_DATA))
        except Exception as exc:
            logger.error("Could not load static_demo.json: %s", exc)
            _DEMO_DATA = {}
    return _DEMO_DATA


def _demo_fallback(query_text: str) -> "PipelineResult":
    """
    Return a pre-baked PipelineResult from static_demo.json.

    Normalisation: lowercase + strip so 'What is X?' and 'what is x?'
    both match the same JSON key.

    Chunk fields 'id' and 'document_id' are optional in the JSON schema;
    sensible defaults are generated when absent so QueryMatch validation
    never fails regardless of how the JSON was authored.

    If no key matches, returns a safe professional default answer that
    guides the recruiter toward a working demo query.
    """
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
            latency_ms=_FALLBACK_LATENCY.copy(),
            cache_hit=False,
        )

    logger.info("Demo fallback — no match for %r, returning default answer.", normalized)
    return PipelineResult(
        answer=_FALLBACK_DEFAULT_ANSWER,
        matches=[],
        latency_ms=_FALLBACK_LATENCY.copy(),
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
    digest = hashlib.sha256(query.strip().lower().encode()).hexdigest()
    return f"infinitum:query:{digest}"


async def _get_redis() -> aioredis.Redis | None:
    """
    Try to open a Redis connection. Returns None — never raises — so the
    caller can always fall back to the live pipeline without crashing.
    """
    try:
        client = aioredis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD or None,
            decode_responses=True,
            socket_connect_timeout=2,
            ssl=True,
        )
        await client.ping()
        return client
    except Exception as exc:
        logger.warning("Redis unavailable (%s) — falling back to live pipeline.", exc)
        return None


async def _pinecone_search(query_text: str, top_k: int) -> list[QueryMatch]:
    search_query = SearchQuery(
        inputs={EMBED_TEXT_FIELD: query_text},
        top_k=top_k,
    )
    loop = asyncio.get_event_loop()
    response = await loop.run_in_executor(
        None,
        partial(_index.search_records, PINECONE_NAMESPACE, search_query),
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
      Cache hit  → answer returned in <5 ms, latency breakdown zeros.
      Cache miss → Pinecone search → NVIDIA generation → Redis write → eval.
      Redis down → graceful fallback, live pipeline runs as normal.

    Fallback mode (any infrastructure exception):
      Logs a WARNING, reads static_demo.json, returns a pre-baked response
      with simulated latency so the UI telemetry panel still renders.
    """
    try:
        clean_query = query_text.strip().lower()

        # ── 0a. Greeting bypass ───────────────────────────────────────────────
        # Strip trailing/leading punctuation before checking so "hi!", "hello?"
        # and "Hey." all resolve correctly. "hi there" still passes through
        # because after stripping it is still two words, not one token.
        _clean_greeting = re.sub(r"[^a-z0-9\s]", "", clean_query).strip()
        if _clean_greeting in _GREETING_TOKENS:
            logger.info("Greeting bypass triggered for %r", clean_query)
            return PipelineResult(
                answer=(
                    "Hello! Welcome to Infinitum AI. I'm your conversational enterprise "
                    "routing assistant. Use the recommended quick-start panels below to "
                    "test live RAG retrievals and our ~2ms caching architecture!"
                ),
                matches=[],
                latency_ms=_ZERO_MS.copy(),
                cache_hit=False,
            )

        # ── 0b. Date / time bypass ────────────────────────────────────────────
        # Triggered only when a DATE_TOKEN appears as a whole word.
        # Using re.findall word-boundary extraction prevents substring false
        # positives: "updates" contains "date" but the extracted word is
        # "updates", which is NOT in _DATE_TOKENS.
        _query_words = set(re.findall(r"\b\w+\b", clean_query))
        if _DATE_TOKENS & _query_words:
            today_str = datetime.date.today().strftime("%A, %B %d, %Y")
            logger.info("Date bypass triggered — returning %s", today_str)
            return PipelineResult(
                answer=(
                    f"Today's system timestamp is {today_str}. "
                    "All telemetry lines and memory-cached pipelines are operating normally."
                ),
                matches=[],
                latency_ms=_ZERO_MS.copy(),
                cache_hit=False,
            )

        total_start = time.perf_counter()

        # ── 1. Cache check ────────────────────────────────────────────────────
        redis = await _get_redis()
        cache_key = _cache_key(query_text)

        if redis:
            try:
                cached_answer = await redis.get(cache_key)
            except RedisError as exc:
                logger.warning("Redis read failed: %s", exc)
                cached_answer = None

            if cached_answer:
                total_ms = round((time.perf_counter() - total_start) * 1000, 2)
                logger.info(
                    "Sub-5ms Cache Hit — total=%.2f ms — key=…%s",
                    total_ms,
                    cache_key[-12:],
                )
                return PipelineResult(
                    answer=cached_answer,
                    matches=[],
                    latency_ms={
                        "retrieval_ms": 0.0,
                        "generation_ms": 0.0,
                        "total_ms": total_ms,
                    },
                    cache_hit=True,
                )

        # ── 2. Retrieval ──────────────────────────────────────────────────────
        retrieval_timer = Timer()
        with track(retrieval_timer):
            matches = await _pinecone_search(query_text, top_k)

        # ── 3. Generation ─────────────────────────────────────────────────────
        contexts = [m.text for m in matches]
        generation_timer = Timer()
        with track(generation_timer):
            answer = await generate_answer_async(query_text, contexts)

        # ── 4. Cache write ────────────────────────────────────────────────────
        if redis:
            try:
                await redis.set(cache_key, answer, ex=CACHE_TTL)
            except RedisError as exc:
                logger.warning("Redis write failed: %s", exc)

        # ── 5. Evaluation ─────────────────────────────────────────────────────
        try:
            evaluate_and_log(query_text, answer, contexts)
        except Exception as exc:
            logger.warning("Evaluator error (non-fatal): %s", exc)

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
