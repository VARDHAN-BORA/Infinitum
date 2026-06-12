from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid


class DocumentIngest(BaseModel):
    """Incoming payload for a document ingestion request."""

    content: str = Field(
        ...,
        min_length=10,
        description="The raw text content to be chunked and indexed.",
    )
    document_id: Optional[str] = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this document. Auto-generated if not provided.",
    )
    source: Optional[str] = Field(
        default=None,
        description="Where this document came from (e.g. 'confluence', 'upload', 'url').",
    )
    metadata: Optional[dict] = Field(
        default_factory=dict,
        description="Arbitrary key-value pairs for filtering later (e.g. department, author).",
    )


class DocumentRecord(BaseModel):
    """Represents a document as tracked in the database after ingestion."""

    document_id: str
    source: Optional[str]
    chunk_count: int
    created_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = Field(
        default="pending",
        description="Lifecycle state: pending | indexed | failed.",
    )


class IngestResponse(BaseModel):
    """Response returned to the caller after a successful ingest request."""

    document_id: str
    chunk_count: int
    status: str
    message: str


class QueryRequest(BaseModel):
    """Incoming payload for a query request."""

    query: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="The user's question or search query.",
    )
    user_id: Optional[str] = Field(
        default=None,
        description="Optional identifier for the requesting user.",
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of matching chunks to return.",
    )


class QueryMatch(BaseModel):
    """A single retrieved chunk returned from Pinecone."""

    id: str = Field(description="Pinecone record ID for this chunk.")
    score: float = Field(description="Semantic similarity score (higher = more relevant).")
    text: str = Field(description="The raw text content of the matched chunk.")
    source: str = Field(description="Origin label of the parent document.")
    document_id: str = Field(description="ID of the parent document this chunk belongs to.")


class QueryResponse(BaseModel):
    """Response returned after a successful retrieval query."""

    query: str
    user_id: Optional[str]
    answer: str
    match_count: int
    matches: list[QueryMatch]
    latency_ms: dict[str, float] = Field(
        description="Breakdown: retrieval_ms, generation_ms, total_ms. "
                    "All zero on a cache hit."
    )
