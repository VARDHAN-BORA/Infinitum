# ∞ Infinitum AI — Enterprise RAG Platform

> **[🚀 Launch Live App Interactive Demo](https://infinitum-1.onrender.com)**

A production-grade **Retrieval-Augmented Generation (RAG)** platform built from scratch,
featuring semantic vector search, Redis semantic caching, multi-tier intent routing,
and a polished Streamlit frontend with live developer telemetry.

---

## ⚡ Performance Optimization Metrics

```
┌─────────────────────────────────────────────────────────────────────┐
│                   LATENCY BENCHMARK RESULTS                         │
├─────────────────────────┬───────────────────────────────────────────┤
│  Live Pipeline (first)  │  ~~1,176 ms  (Pinecone + NVIDIA LLM)       │
│  Redis Cache Hit        │    ~186 ms  (SHA-256 key lookup)          │
│  Latency Reduction      │   84.2%  ████████████████████████░░░░     │
│  Intent Bypass          │    ~0 ms    (Greetings/date queries)      │
└─────────────────────────┴───────────────────────────────────────────┘
```

> **Note:** Benchmarks measured on Render free tier (0.1 CPU, shared infrastructure).
> Local benchmarks show **99.8% latency reduction** (1,058ms → 2ms) with dedicated Redis.

After the first query, identical questions are served from Redis cache — skipping
Pinecone retrieval and NVIDIA generation entirely.

---


<img width="1443" height="785" alt="Query" src="https://github.com/user-attachments/assets/440644f8-a324-4957-90b1-b7021f138e7c" />
<img width="1433" height="778" alt="Cache Hit" src="https://github.com/user-attachments/assets/42abc41d-699a-440b-8b7e-55b938f4cdd2" />

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
║   │       REDIS SEMANTIC CACHE (~446 ms)    │                    ║
║   │  Key: SHA-256(query.strip().lower())    │                    ║
║   │  TTL: 3600s  │  HIT → return instantly  │                    ║
║   └─────────────────┬───────────────────────┘                    ║
║                     │ CACHE MISS                                 ║
║                     ▼                                            ║
║   ┌─────────────────────────────────────────┐                    ║
║   │    PINECONE VECTOR RETRIEVAL (~986 ms)  │                    ║
║   │  index.search_records()                 │                    ║
║   │  llama-text-embed-v2 (integrated embed) │                    ║
║   │  Returns top-k semantically ranked hits │                    ║
║   └─────────────────┬───────────────────────┘                    ║
║                     ▼                                            ║
║   ┌─────────────────────────────────────────┐                    ║
║   │    NVIDIA LLM GENERATION (~390 ms)      │                    ║
║   │  nvidia/llama-3.1-nemotron-nano-8b-v1  │                    ║
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
| **LLM Generation** | NVIDIA API — `nvidia/llama-3.1-nemotron-nano-8b-v1` |
| **Semantic Cache** | Redis (Upstash) — SHA-256 keyed, 1-hour TTL, TLS/SSL |
| **Text Splitting** | LangChain `RecursiveCharacterTextSplitter` |
| **Data Validation** | Pydantic v2 + Pydantic Settings |
| **Frontend UI** | Streamlit 1.41 — chat interface + live developer telemetry |
| **Evaluation** | Custom heuristic RAGAS harness (faithfulness + relevance) |
| **Config** | `.env` via Pydantic Settings — zero hardcoded secrets |
| **Deployment** | Render + Upstash Redis |

---

## 📚 What Kind of RAG Is This? (The Knowledge Base Explained)

> **Short answer:** This is a simulated **enterprise internal knowledge base** — the kind of private company documentation that employees need to search, but which can never be sent to a public AI. Infinitum lets you ask natural language questions against your own private documents, securely and locally.

The system has **3 indexed documents** representing a fictional company's internal runbooks:

---

### 📋 Document 1 — `compliance_manual.txt` (Infrastructure Compliance)
**What it covers:** 2026 internal engineering mandates — API routing rules, telemetry logging requirements, and Redis cache targets.

**Ask questions like:**
```
What are the logging requirements for microservices?
How often are logs shipped to the security monitor?
What is the Redis cache hit target?
What are the 2026 updates for routing and logging protocols?
```

---

### 🗄️ Document 2 — `database_policy.txt` (Vector Storage Policy)
**What it covers:** Pinecone/vector database configuration — index dimensions, connection pooling rules, and socket protection.

**Ask questions like:**
```
What vector dimensions should we use for text embeddings?
What is the maximum idle timeout for database connections?
How should engineering teams scale vector namespaces?
```

---

### 🚀 Document 3 — `deployment_guide.txt` (CI/CD Runbook)
**What it covers:** Continuous deployment rules — test coverage requirements, container health checks, and telemetry tracing.

**Ask questions like:**
```
What test coverage percentage is required before deployment?
What must pass before code goes to the live cluster?
What do telemetry spans track?
```

---

### 💬 Conversational Queries (No Documents Needed)

| Query type | Example | Response time |
|---|---|---|
| Greetings | `hi`, `hello!`, `hey` | 0 ms |
| Date / Time | `what's today's date?` | 0 ms |
| Knowledge base overview | `what data do you have?` | ~1,905 ms (live RAG) |

---
<img width="1389" height="756" alt="Greetings" src="https://github.com/user-attachments/assets/a40bcc19-c046-4451-bcbf-973947d842dc" />

## 🚀 Quick Start

### 1. Setup

```bash
git clone https://github.com/VARDHAN-BORA/Infinitum && cd Infinitum
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in your keys:

```bash
PINECONE_API_KEY=your_key_here
PINECONE_INDEX_NAME=llama-text-embed-v2-index
NVIDIA_API_KEY=your_key_here
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=           # required for Upstash in production
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

## 📁 Project Structure

```
infinitum/
├── app/
│   ├── main.py              # FastAPI routes (/health, /v1/query, /v1/ingest)
│   ├── query.py             # RAG pipeline — intent router, cache, retrieval, eval
│   ├── ingestion.py         # Document chunking + Pinecone upsert
│   ├── llm.py               # NVIDIA client + 3-mode system prompt
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

## 🌐 Deployment

| Service | Platform |
|---|---|
| **FastAPI Backend** | Render (Free) |
| **Streamlit Frontend** | Render (Free) |
| **Redis Cache** | Upstash (Free) — TLS/SSL enabled |

> ⚠️ Free tier instances spin down after 15 min of inactivity. First request may take 30–60s to wake up.

---

## 🔬 Edge Case Audit & Failure Handling

**6 bugs found and fixed** during systematic edge-case audit:

| # | Bug | Severity | Fix |
|---|---|---|---|
| 1 | Date bypass false positive (`"updates"` contains `"date"`) | Critical | Whole-word regex token extraction |
| 2 | Greeting bypass ignored punctuation (`"hi!"` fell through) | High | Strip non-alphanumeric before frozenset check |
| 3 | Evaluator false drift warning on stop-word answers | Medium | Return neutral `0.5` when answer tokens empty |
| 4 | Mutable shared dict returned by reference | Medium | `.copy()` on all return sites |
| 5 | Whitespace-only query bypassed Pydantic validation | Medium | `@field_validator` strips and rejects blank queries |
| 6 | Intent router misidentified as Redis cache in UI badge | Low | Added explicit `cache_hit: bool` field to response |

### Infrastructure Resilience

| Failure | Behaviour |
|---|---|
| **Redis unreachable** | Falls back to live pipeline within 1s timeout |
| **Pinecone down** | Serves pre-baked demo answers from `static_demo.json` |
| **NVIDIA rate limit** | Same demo fallback with simulated realistic latency |
| **`static_demo.json` missing** | Returns default guidance message gracefully |
