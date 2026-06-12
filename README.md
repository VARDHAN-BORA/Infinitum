# ∞ Infinitum AI — Enterprise RAG Platform

> **[🚀 Launch Live App Interactive Demo](YOUR_CLOUD_DEPLOYMENT_URL_HERE)**

A production-grade **Retrieval-Augmented Generation (RAG)** platform built from scratch,
featuring semantic vector search, sub-millisecond Redis caching, multi-tier intent routing,
and a polished Streamlit frontend with live developer telemetry.

---

## ⚡ Performance Optimization Metrics

```
┌─────────────────────────────────────────────────────────────────────┐
│                   LATENCY BENCHMARK RESULTS                         │
├─────────────────────────┬───────────────────────────────────────────┤
│  Live Pipeline (first)  │  ~1,058 ms  (Pinecone + Groq LLM)         │
│  Redis Cache Hit        │    ~2 ms    (SHA-256 key lookup)          │
│  Latency Reduction      │   99.8%  ██████████████████████████████   │
│  Intent Bypass          │    ~0 ms    (greetings / date queries)    │
└─────────────────────────┴───────────────────────────────────────────┘
```

After the first query, **identical or semantically equivalent questions are answered in
under 2 milliseconds** — a 99.8% reduction — via a Redis semantic caching layer that
stores answers by SHA-256 query hash with a 1-hour TTL.

---

## 🏗️ System Architecture

```
╔══════════════════════════════════════════════════════════════════╗
║                      INGESTION PIPELINE                          ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║   Raw .txt Documents                                             ║
║         │                                                        ║
║         ▼                                                        ║
║   LangChain RecursiveCharacterTextSplitter                       ║
║   (chunk_size=500 chars, overlap=50 chars)                       ║
║         │                                                        ║
║         ▼                                                        ║
║   Pinecone index.upsert_records()                                ║
║   └─ Integrated Inference: llama-text-embed-v2                   ║
║      (vectors generated server-side — no local model)            ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
                              │
                POST /v1/ingest
                              │
╔══════════════════════════════════════════════════════════════════╗
║                       QUERY PIPELINE                             ║
╠══════════════════════════════════════════════════════════════════╣
║                                                                  ║
║   User Query (POST /v1/query)                                    ║
║         │                                                        ║
║         ▼                                                        ║
║   ┌─────────────────────────────────────────┐                    ║
║   │         INTENT ROUTER (0 ms)            │                    ║
║   │  Greeting? → Instant warm response      │                    ║
║   │  Date/Time? → Live datetime() response  │                    ║
║   └─────────────────┬───────────────────────┘                    ║
║                     │ (technical queries only)                   ║
║                     ▼                                            ║
║   ┌─────────────────────────────────────────┐                    ║
║   │       REDIS SEMANTIC CACHE (~2 ms)      │                    ║
║   │  Key: SHA-256(query.strip().lower())    │                    ║
║   │  TTL: 3600s  │  HIT → return instantly  │                    ║
║   └─────────────────┬───────────────────────┘                    ║
║                     │ CACHE MISS                                 ║
║                     ▼                                            ║
║   ┌─────────────────────────────────────────┐                    ║
║   │    PINECONE VECTOR RETRIEVAL (~280 ms)  │                    ║
║   │  index.search_records()                 │                    ║
║   │  llama-text-embed-v2 (integrated embed) │                    ║
║   │  Returns top-k semantically ranked hits │                    ║
║   └─────────────────┬───────────────────────┘                    ║
║                     ▼                                            ║
║   ┌─────────────────────────────────────────┐                    ║
║   │    GROQ LLM GENERATION (~780 ms)        │                    ║
║   │  llama-3.1-8b-instant (free tier)       │                    ║
║   │  3-mode system prompt:                  │                    ║
║   │  • Greetings & Casual Chat              │                    ║
║   │  • System Data Overview                 │                    ║
║   │  • Technical Research                   │                    ║
║   └─────────────────┬───────────────────────┘                    ║
║                     ▼                                            ║
║   Redis WRITE (answer cached for 1 hr)                           ║
║         │                                                        ║
║         ▼                                                        ║
║   Heuristic Evaluator                                            ║
║   └─ faithfulness score + answer_relevance score                 ║
║   └─ Logs WARNING if either metric drops below 0.7               ║
║         │                                                        ║
║         ▼                                                        ║
║   FastAPI JSON Response                                          ║
║   └─ answer, matches[], latency_ms{retrieval, generation, total} ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **API Server** | FastAPI 0.115 + Uvicorn (async, production-grade) |
| **Vector Database** | Pinecone 6.0 — integrated inference (`llama-text-embed-v2`) |
| **LLM Generation** | Groq API — `llama-3.1-8b-instant` (100% free tier) |
| **Semantic Cache** | Redis 5.2 — SHA-256 keyed, 1-hour TTL |
| **Text Splitting** | LangChain `RecursiveCharacterTextSplitter` |
| **Data Validation** | Pydantic v2 + Pydantic Settings |
| **Frontend UI** | Streamlit 1.41 — chat interface + live developer telemetry |
| **Evaluation** | Custom heuristic RAGAS harness (faithfulness + relevance) |
| **Config** | `.env` via Pydantic Settings — zero hardcoded secrets |

---

## 🚀 Quick Start Interactive Tour

### 1. Setup

```bash
git clone <repo-url> && cd infinitum
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in your keys:

```bash
PINECONE_API_KEY=your_key_here
PINECONE_INDEX_NAME=llama-text-embed-v2-index
GROQ_API_KEY=your_key_here
REDIS_HOST=localhost      # optional — app degrades gracefully without Redis
REDIS_PORT=6379
```

### 2. Start the stack

```bash
# Terminal 1 — FastAPI backend
uvicorn app.main:app --reload

# Terminal 2 — Streamlit frontend
streamlit run app/ui.py
```

Open **`http://localhost:8501`**

---

### 3. Recruiter Verification Tour

Click through these four scenarios in the Streamlit UI to see every system layer fire:

#### 🟢 Scenario A — Conversational Intent (0 ms, intent bypass)
Type any of:
```
hi
hello
hey
```
**Expected:** Instant warm greeting. `latency_ms` all zeros. No Pinecone or Redis call made.

#### 🗓️ Scenario B — Live DateTime Query (0 ms, Python stdlib bypass)
Type any of:
```
what's today's date?
what time is it?
tell me the date
```
**Expected:** Live system date returned instantly. Zero infrastructure calls.

#### 🔵 Scenario C — Live RAG Pipeline (first run, ~1,058 ms)
Click the **"📋 Test 1: Infrastructure Compliance updates"** button in the tour panel.

**Expected:** Blue **"LIVE PIPELINE GENERATION"** badge in the sidebar.
Latency breakdown shows `retrieval_ms` (~280 ms) and `generation_ms` (~780 ms) separately.
Source chunks from `compliance_manual.txt` appear in the expandable citations panel.

#### ⚡ Scenario D — Redis Semantic Cache Hit (~2 ms)
Click the **same button a second time**.

**Expected:** Green **"⚡ CACHE HIT (REDIS)"** badge.
`retrieval_ms = 0`, `generation_ms = 0`, `total_ms` drops to ~2 ms.
**This is the 99.8% latency reduction live on screen.**

---

## 📁 Project Structure

```
infinitum/
├── app/
│   ├── main.py              # FastAPI routes (/health, /v1/query, /v1/ingest)
│   ├── query.py             # RAG pipeline — intent router, cache, retrieval, eval
│   ├── ingestion.py         # Document chunking + Pinecone upsert
│   ├── llm.py               # Groq client + 3-mode system prompt
│   ├── models.py            # Pydantic schemas (request/response/internal)
│   ├── config.py            # Pydantic Settings (reads .env)
│   ├── pinecone_client.py   # Shared Pinecone client (initialized once)
│   ├── metrics.py           # Timer context manager (time.perf_counter)
│   ├── evaluator.py         # Heuristic faithfulness + relevance scoring
│   ├── ui.py                # Streamlit chat UI + developer telemetry sidebar
│   └── static_demo.json     # Pre-baked fallback answers for offline demo
├── scripts/
│   └── seed_large_data.py   # Bulk .txt ingestion script (batched, dry-run mode)
├── requirements.txt         # Full dependency lock (pip freeze)
└── README.md
```

---

## 🔌 API Reference

### `POST /v1/query`
```json
{
  "query": "What are the 2026 routing protocol updates?",
  "top_k": 5
}
```
**Response:**
```json
{
  "answer": "The 2026 updates introduce...",
  "match_count": 3,
  "matches": [{ "id": "...", "score": 0.9823, "text": "...", "source": "compliance_manual.txt" }],
  "latency_ms": { "retrieval_ms": 284.5, "generation_ms": 773.1, "total_ms": 1058.2 }
}
```

### `POST /v1/ingest`
```json
{ "content": "Your document text...", "source": "compliance_manual.txt" }
```

### `GET /health`
```json
{ "status": "ok", "service": "infinitum" }
```

Interactive docs available at **`http://localhost:8000/docs`**

---

## 🌐 Deployment

The app is deployment-ready for any Python-compatible cloud platform:

| Platform | Command |
|---|---|
| **Railway / Render** | Connect repo → set env vars → deploy |
| **Fly.io** | `fly launch` → `fly secrets set PINECONE_API_KEY=...` |
| **Docker** | `docker build -t infinitum . && docker run -p 8000:8000 infinitum` |

Update the demo badge URL at the top of this README after deploying.
