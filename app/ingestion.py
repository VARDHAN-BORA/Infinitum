import asyncio
from functools import partial

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.models import DocumentIngest, DocumentRecord
from app.pinecone_client import EMBED_TEXT_FIELD, PINECONE_NAMESPACE, get_index

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

# Built once at startup — cheap to create, wasteful to recreate per request.
_splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    keep_separator=True,
)


def split_document(content: str) -> list[str]:
    """Split raw text into overlapping chunks."""
    return _splitter.split_text(content)


def _build_records(
    document_id: str, chunks: list[str], source: str | None
) -> list[dict]:
    """
    Shape each chunk into a Pinecone record.

    Because our index uses integrated inference, we pass raw text in the
    EMBED_TEXT_FIELD — Pinecone's llama-text-embed-v2 model converts it to a
    vector internally. We never touch embeddings locally.

    _id format: "<document_id>_chunk_<index>" so every chunk is addressable
    individually and can be deleted or updated later without touching others.
    """
    return [
        {
            "_id": f"{document_id}_chunk_{i}",
            EMBED_TEXT_FIELD: chunk,
            "source": source or "unknown",
            "chunk_index": i,
            "document_id": document_id,
        }
        for i, chunk in enumerate(chunks)
    ]


async def _pinecone_upsert(
    document_id: str, chunks: list[str], source: str | None
) -> None:
    """
    Push records to Pinecone asynchronously.

    The Pinecone SDK is synchronous, so we offload it to a thread-pool
    executor. This keeps the FastAPI event loop free to handle other
    requests while the network call is in flight.
    """
    records = _build_records(document_id, chunks, source)
    loop = asyncio.get_event_loop()
    index = get_index()
    await loop.run_in_executor(
        None,
        partial(index.upsert_records, PINECONE_NAMESPACE, records),
    )


async def ingest_document(payload: DocumentIngest) -> DocumentRecord:
    """
    Full ingestion pipeline:
      1. Split text into overlapping chunks.
      2. Upsert raw text records to Pinecone (integrated inference embeds them).
      3. Return a DocumentRecord for downstream database tracking.
    """
    chunks = split_document(payload.content)
    await _pinecone_upsert(payload.document_id, chunks, payload.source)

    return DocumentRecord(
        document_id=payload.document_id,
        source=payload.source,
        chunk_count=len(chunks),
        status="indexed",
    )
