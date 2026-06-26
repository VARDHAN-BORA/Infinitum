from fastapi import FastAPI, HTTPException
from app.models import DocumentIngest, IngestResponse, QueryRequest, QueryResponse

app = FastAPI(
    title="Infinitum",
    description="Enterprise-grade Production RAG Platform",
    version="0.1.0",
)


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "service": "infinitum"}


@app.post("/v1/query", response_model=QueryResponse, tags=["RAG"])
async def query(payload: QueryRequest):
    from app.query import run_rag_pipeline
    try:
        result = await run_rag_pipeline(payload.query, top_k=payload.top_k)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Unrecoverable pipeline error: {exc}")
    return QueryResponse(
        query=payload.query,
        user_id=payload.user_id,
        answer=result.answer,
        match_count=len(result.matches),
        matches=result.matches,
        latency_ms=result.latency_ms,
        cache_hit=result.cache_hit,
    )


@app.post("/v1/ingest", response_model=IngestResponse, tags=["Ingestion"])
async def ingest(payload: DocumentIngest):
    from app.ingestion import ingest_document
    try:
        record = await ingest_document(payload)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Pinecone upsert failed: {exc}")
    return IngestResponse(
        document_id=record.document_id,
        chunk_count=record.chunk_count,
        status=record.status,
        message=f"Document split into {record.chunk_count} chunks and indexed via llama-text-embed-v2.",
    )
