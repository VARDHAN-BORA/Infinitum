import asyncio
from functools import partial

from openai import OpenAI

from app.config import settings

MODEL = "deepseek-ai/deepseek-v4-flash"

_client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=settings.NVIDIA_API_KEY,
)

_SYSTEM_PROMPT = """You are Infinitum AI, an advanced Enterprise RAG platform assistant. \
You have access to retrieved system document context chunks.

Follow these strict output guidelines:

1. GREETINGS & CASUAL CHAT: If the user greets you, asks how you are, or engages in \
casual conversation, respond naturally, warmly, and professionally. \
Do not require technical data to say hello.

2. SYSTEM DATA OVERVIEW: If the user asks what data you have or to summarize your \
knowledge base, look at the retrieved source chunks and provide a clear, simple summary \
of the files currently indexed \
(e.g., compliance_manual.txt, database_policy.txt, deployment_guide.txt).

3. TECHNICAL RESEARCH: If the user asks a specific technical question about \
infrastructure, compliance, or system parameters, cross-reference the retrieved chunks. \
If the context does not contain sufficient information to answer that specific technical \
inquiry, state: "The available knowledge base does not contain sufficient information to \
answer this question." smoothly."""


def generate_answer(query: str, contexts: list[str]) -> str:
    """
    Synchronous generation call — kept sync because the OpenAI SDK is synchronous.
    Call generate_answer_async() from async code so the event loop stays free.

    The user message always reaches the model regardless of whether context
    chunks exist. Empty context is surfaced as an explicit label so the model
    can still respond naturally to greetings or casual queries without chunks.
    """
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

    response = _client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        temperature=0.2,  # slightly warmer than before — natural for greetings,
                          # still disciplined enough for factual technical answers
        max_tokens=512,
    )

    return response.choices[0].message.content.strip()


async def generate_answer_async(query: str, contexts: list[str]) -> str:
    """
    Async wrapper around generate_answer().

    Offloads the blocking NVIDIA network call to a thread-pool executor so the
    FastAPI event loop remains free to handle other requests in parallel.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        partial(generate_answer, query, contexts),
    )
