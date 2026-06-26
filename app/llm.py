import asyncio
from functools import partial

import httpx
from openai import OpenAI

from app.config import settings

MODEL = "meta/llama-3.1-8b-instruct"

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=settings.NVIDIA_API_KEY,
            timeout=httpx.Timeout(30.0, connect=5.0),
        )
    return _client


_SYSTEM_PROMPT = (
    "You are Infinitum AI, an Enterprise RAG assistant. "
    "Answer based ONLY on the provided context chunks. "
    "Cite sources using [1], [2], etc. matching the chunk numbers. "
    "If context is insufficient to answer, say: "
    '"The available knowledge base does not contain sufficient information '
    'to answer this question."'
)


def generate_answer(query: str, contexts: list[str]) -> str:
    if contexts:
        context_block = "\n\n".join(
            f"[{i + 1}] {ctx}" for i, ctx in enumerate(contexts)
        )
    else:
        context_block = "(No context chunks were retrieved for this query.)"

    user_message = (
        f"Retrieved Context Chunks:\n{context_block}"
        f"\n\nUser Query: {query}"
    )

    response = _get_client().chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        temperature=0.2,
        max_tokens=384,
    )

    return response.choices[0].message.content.strip()


async def generate_answer_async(query: str, contexts: list[str]) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        partial(generate_answer, query, contexts),
    )
