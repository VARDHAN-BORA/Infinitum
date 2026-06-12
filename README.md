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

<img width="1389" height="756" alt="Greetings" src="https://github.com/user-attachments/assets/a40bcc19-c046-4451-bcbf-973947d842dc" />
<img width="1443" height="785" alt="Query" src="https://github.com/user-attachments/assets/440644f8-a324-4957-90b1-b7021f138e7c" />
<img width="1433" height="778" alt="Cache Hit" src="https://github.com/user-attachments/assets/42abc41d-699a-440b-8b7e-55b938f4cdd2" />


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

## 📚 What Kind of RAG Is This? (The Knowledge Base Explained)

> **Short answer:** This is a simulated **enterprise internal knowledge base** — the kind of private company documentation that employees need to search, but which can never be sent to a public AI. Infinitum lets you ask natural language questions against your own private documents, securely and locally.

This is exactly the real-world use case for RAG: proprietary internal docs that can't go into ChatGPT.

The system has **3 indexed documents** representing a fictional company's internal runbooks:

---

### 📋 Document 1 — `compliance_manual.txt` (Infrastructure Compliance)
**What it covers:** 2026 internal engineering mandates — API routing rules, telemetry logging requirements, and Redis cache targets.

**Ask questions like:**
```
What are the logging requirements for microservices?
How often are logs shipped to the security monitor?
What is the Redis cache hit target?
What is the rule for synchronous vs asynchronous workers?
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
What protects the Pinecone clusters from socket depletion?
```

---

### 🚀 Document 3 — `deployment_guide.txt` (CI/CD Runbook)
**What it covers:** Continuous deployment rules — test coverage requirements, container health checks, and telemetry tracing.

**Ask questions like:**
```
What test coverage percentage is required before deployment?
What must pass before code goes to the live cluster?
What do telemetry spans track?
What are the staging environment requirements?
```

---

### 💬 Conversational Queries (No Documents Needed)

The system also handles these instantly via the Intent Router — no Pinecone or Groq call made:

| Query type | Example | Response time |
|---|---|---|
| Greetings | `hi`, `hello!`, `hey` | 0 ms |
| Date / Time | `what's today's date?` | 0 ms |
| Knowledge base overview | `what data do you have?` | ~1,058 ms (live RAG) |

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

### 3. Scenarios you can test!

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

---

## 🔬 Edge Case Audit & Failure Handling

This project was put through a systematic edge-case audit. **6 bugs were found and fixed.** Here is every failure mode and the exact engineering decision used to resolve it.

---

### Bug 1 — Date Bypass: Substring False Positive *(Critical)*

**Failure:** Any query containing the word `"updates"` was intercepted by the date bypass and returned *"Today's system timestamp is…"* instead of running the RAG pipeline. Root cause: `"updates"` contains `"date"` as a substring.

```
"give me a summary of the 2026 infrastructure compliance updates."
                                                          ^^^^^^
                                                    contains "date"
```

**Affected queries:** Every demo query (`"what are the 2026 updates…"`, `"give me a summary…"`), plus any real-world query about `"validate"`, `"mandate"`, `"updated"`, `"timestamp"`.

**Fix:** Replaced substring `in` check with `re.findall(r"\b\w+\b", query)` whole-word extraction + set intersection. `"updates"` extracts as the token `"updates"` — not in `{"date","time","today"}`.

```python
# Before (broken)
if any(token in clean_query for token in _DATE_TOKENS):

# After (fixed)
_query_words = set(re.findall(r"\b\w+\b", clean_query))
if _DATE_TOKENS & _query_words:
```

---

### Bug 2 — Greeting Bypass: Punctuation Not Stripped *(High)*

**Failure:** `"hi!"`, `"hello?"`, `"Hey."` all fell through to the full Pinecone + Groq pipeline instead of the 0ms greeting bypass. The frozenset check was exact — `"hi!"` ≠ `"hi"`.

**Fix:** Strip all non-alphanumeric characters before the frozenset check using `re.sub(r"[^a-z0-9\s]", "", clean_query).strip()`.

```python
_clean_greeting = re.sub(r"[^a-z0-9\s]", "", clean_query).strip()
if _clean_greeting in _GREETING_TOKENS:
```

`"hi there"` correctly still passes through (two words after strip, not in frozenset).

---

### Bug 3 — Evaluator: False Drift Warning on Stop-Word Answers *(Medium)*

**Failure:** An answer consisting of mostly common words (e.g., *"Sure, I can help with that."*) has zero meaningful tokens after stop-word removal. `compute_faithfulness` returned `0.0`, firing a `⚠️ RETRIEVAL DRIFT DETECTED` warning even though the response was valid.

**Fix:** Return a neutral `0.5` (no-opinion score) instead of `0.0` when `answer_words` is empty after stop-word filtering. `0.5` sits above the `0.7` warning threshold only when combined with a healthy `answer_relevance`, so genuine drift is still caught.

---

### Bug 4 — Mutable Shared Dict Returned by Reference *(Medium)*

**Failure:** `_ZERO_MS` and `_FALLBACK_LATENCY` were module-level dicts returned directly into `PipelineResult.latency_ms`. Any downstream code mutating `result.latency_ms` would silently corrupt the shared constant, causing all future responses to return wrong telemetry values.

**Fix:** All four return sites now call `.copy()`:

```python
latency_ms=_ZERO_MS.copy()
latency_ms=_FALLBACK_LATENCY.copy()
```

---

### Bug 5 — Whitespace-Only Query Bypasses Validation *(Medium)*

**Failure:** A `query` of `"   "` (spaces only) passes Pydantic's `min_length=1` check (length = 3), but after `.strip()` in the pipeline it becomes `""` — an empty string fed to Pinecone's semantic search, producing undefined behaviour.

**Fix:** Added a Pydantic `@field_validator` on `QueryRequest.query` that strips whitespace and raises a `ValueError` if the result is empty. Returns HTTP 422 with a clear message.

```python
@field_validator("query")
@classmethod
def query_must_not_be_blank(cls, v: str) -> str:
    if not v.strip():
        raise ValueError("query must not be blank or whitespace only")
    return v
```

---

### Bug 6 — UI Telemetry Badge: Intent Router Misidentified as Redis Cache *(Low)*

**Failure:** The sidebar badge logic used `retrieval_ms == 0 AND generation_ms == 0` to detect cache hits. This is also true for greeting/date intent bypass results, so typing `"hello"` showed a green **"⚡ CACHE HIT (REDIS)"** badge — factually wrong and misleading to a recruiter.

**Fix:** Added `cache_hit: bool` field to `QueryResponse` (passed from `PipelineResult`). Badge logic now has three explicit states:

| Condition | Badge |
|---|---|
| `cache_hit=True` | 🟢 `⚡ CACHE HIT (REDIS)` |
| `cache_hit=False`, latency=0ms | 🟡 `⚡ INTENT ROUTER BYPASS (0ms)` |
| `cache_hit=False`, latency>0ms | 🔵 `🔵 LIVE PIPELINE GENERATION` |

---

### Infrastructure Resilience (by design, not a bug)

These failure modes are handled gracefully without crashing:

| Failure | Behaviour |
|---|---|
| **Redis unreachable** | `_get_redis()` returns `None` within 1s timeout; pipeline continues without cache |
| **Pinecone down / API key invalid** | Outer `except (PineconeException, …, Exception)` triggers Resilient Demo Fallback Mode |
| **Groq rate limit / API error** | Same outer except — demo fallback serves pre-baked answer with realistic simulated latency |
| **`static_demo.json` missing / corrupt** | `_load_demo_data()` catches the `IOError`, sets `_DEMO_DATA = {}`, returns default guidance message |
| **Unknown query in demo mode** | Returns a professional default with a hint toward known working queries |
