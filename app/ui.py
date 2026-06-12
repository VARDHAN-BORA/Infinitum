"""
Infinitum AI — Recruiter-facing chat interface.

Run with:
    streamlit run app/ui.py

Requires the FastAPI server to be running:
    uvicorn app.main:app --reload
"""

import re
import requests
import streamlit as st

API_BASE = "http://localhost:8000"
DEFAULT_TOP_K = 5

# ── Page config (must be first Streamlit call) ────────────────────────────────
st.set_page_config(
    page_title="Infinitum AI",
    page_icon="∞",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global styles ─────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
        /* ---- typography ---- */
        html, body, [class*="css"] { font-family: "Inter", sans-serif; }

        /* ---- header ---- */
        .infinitum-header {
            display: flex; align-items: center; gap: 12px;
            padding: 0.4rem 0 1.2rem 0; border-bottom: 1px solid #e2e8f0;
            margin-bottom: 1.2rem;
        }
        .infinitum-logo {
            font-size: 2.4rem; font-weight: 800;
            background: linear-gradient(135deg, #6366f1, #8b5cf6);
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        }
        .infinitum-title { font-size: 1.35rem; font-weight: 700; color: #1e293b; }
        .infinitum-subtitle { font-size: 0.82rem; color: #64748b; }

        /* ---- cache badges ---- */
        .badge {
            display: inline-flex; align-items: center; gap: 6px;
            padding: 8px 16px; border-radius: 999px;
            font-size: 0.78rem; font-weight: 700; letter-spacing: 0.05em;
            text-transform: uppercase; width: 100%;
            justify-content: center; margin: 0.5rem 0 1rem 0;
        }
        .badge-cache {
            background: #dcfce7; color: #15803d;
            border: 1.5px solid #86efac;
        }
        .badge-live {
            background: #dbeafe; color: #1d4ed8;
            border: 1.5px solid #93c5fd;
        }

        /* ---- metric cards ---- */
        .metric-row { display: flex; gap: 8px; margin-bottom: 0.8rem; }
        .metric-card {
            flex: 1; background: #f8fafc; border: 1px solid #e2e8f0;
            border-radius: 10px; padding: 10px 12px; text-align: center;
        }
        .metric-label {
            font-size: 0.68rem; color: #94a3b8;
            text-transform: uppercase; letter-spacing: 0.06em;
        }
        .metric-value {
            font-size: 1.15rem; font-weight: 700; color: #0f172a;
            margin-top: 2px;
        }

        /* ---- source chips ---- */
        .source-chip {
            display: inline-block; background: #f1f5f9;
            border: 1px solid #e2e8f0; color: #475569;
            border-radius: 6px; padding: 2px 10px;
            font-size: 0.75rem; margin: 2px 4px 2px 0;
        }

        /* ---- citation markers ---- */
        .cite {
            display: inline-flex; align-items: center; justify-content: center;
            width: 18px; height: 18px; background: #6366f1; color: white;
            border-radius: 50%; font-size: 0.65rem; font-weight: 700;
            vertical-align: super; margin: 0 1px;
        }

        /* ---- answer box ---- */
        .answer-box {
            background: #fafafa; border-left: 3px solid #6366f1;
            border-radius: 0 10px 10px 0; padding: 1rem 1.2rem;
            line-height: 1.7; color: #1e293b;
        }

        /* ---- RAG verification tour ---- */
        .tour-panel {
            background: linear-gradient(135deg, #f5f3ff, #eff6ff);
            border: 1.5px solid #c4b5fd;
            border-radius: 14px;
            padding: 1rem 1.25rem 0.85rem;
            margin: 1.2rem 0 0.6rem;
        }
        .tour-header {
            font-size: 0.88rem; font-weight: 700;
            color: #4338ca; margin-bottom: 0.75rem;
        }
        .tour-tip {
            font-size: 0.76rem; color: #6366f1;
            margin-top: 0.65rem; font-style: italic;
            line-height: 1.5;
        }

        /* ---- chat input override ---- */
        .stChatInputContainer { padding-top: 0.5rem; }

        /* ---- hide Streamlit branding ---- */
        #MainMenu, footer, header { visibility: hidden; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ── Helper functions ──────────────────────────────────────────────────────────

def _format_citations(text: str) -> str:
    """Wrap [N] markers with a styled span."""
    return re.sub(
        r"\[(\d+)\]",
        r'<span class="cite">\1</span>',
        text,
    )


def _query_api(query: str, top_k: int) -> dict | None:
    try:
        resp = requests.post(
            f"{API_BASE}/v1/query",
            json={"query": query, "top_k": top_k},
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        st.error(
            "Cannot connect to the Infinitum API. "
            "Start the server with: `uvicorn app.main:app --reload`"
        )
        return None
    except requests.exceptions.HTTPError as exc:
        st.error(f"API returned {exc.response.status_code}: {exc.response.text}")
        return None
    except Exception as exc:
        st.error(f"Unexpected error: {exc}")
        return None


def _render_telemetry(latency: dict[str, float], cache_hit: bool) -> None:
    """Render the developer telemetry panel in the sidebar."""
    is_cache = cache_hit or (
        latency.get("retrieval_ms", 1) == 0.0
        and latency.get("generation_ms", 1) == 0.0
    )

    if is_cache:
        st.sidebar.markdown(
            '<div class="badge badge-cache">⚡ Cache Hit (Redis)</div>',
            unsafe_allow_html=True,
        )
    else:
        st.sidebar.markdown(
            '<div class="badge badge-live">🔵 Live Pipeline Generation</div>',
            unsafe_allow_html=True,
        )

    retrieval = latency.get("retrieval_ms", 0.0)
    generation = latency.get("generation_ms", 0.0)
    total = latency.get("total_ms", 0.0)

    st.sidebar.markdown(
        f"""
        <div class="metric-row">
            <div class="metric-card">
                <div class="metric-label">Retrieval</div>
                <div class="metric-value">{retrieval:.0f} ms</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Generation</div>
                <div class="metric-value">{generation:.0f} ms</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Total</div>
                <div class="metric-value">{total:.0f} ms</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Session state ─────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []  # [{role, content, data}]

if "last_telemetry" not in st.session_state:
    st.session_state.last_telemetry = None

# Holds a query string pre-filled by a suggestion button click.
# Consumed once per run so it never fires twice.
if "pending_query" not in st.session_state:
    st.session_state.pending_query = None


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        '<div style="font-size:1.6rem;font-weight:800;'
        'background:linear-gradient(135deg,#6366f1,#8b5cf6);'
        '-webkit-background-clip:text;-webkit-text-fill-color:transparent;">'
        "∞ Infinitum AI</div>",
        unsafe_allow_html=True,
    )
    st.caption("Enterprise RAG Platform")
    st.divider()

    top_k = st.slider(
        "Chunks to retrieve (top_k)",
        min_value=1, max_value=20, value=DEFAULT_TOP_K,
        help="How many context chunks to pull from Pinecone per query.",
    )

    st.divider()

    with st.expander("🛠 Developer Telemetry & Analytics", expanded=True):
        if st.session_state.last_telemetry:
            data = st.session_state.last_telemetry
            _render_telemetry(
                data.get("latency_ms", {}),
                data.get("cache_hit", False),
            )
            match_count = data.get("match_count", 0)
            st.caption(f"Context chunks used: **{match_count}**")
        else:
            st.info("Telemetry will appear here after your first query.", icon="📊")

    st.divider()
    if st.button("🗑 Clear conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.last_telemetry = None
        st.rerun()


# ── Main header ───────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="infinitum-header">
        <div class="infinitum-logo">∞</div>
        <div>
            <div class="infinitum-title">Infinitum AI</div>
            <div class="infinitum-subtitle">
                Ask anything — powered by Pinecone · llama-text-embed-v2 · Llama 3 · Redis
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Welcome message ───────────────────────────────────────────────────────────
if not st.session_state.messages:
    st.markdown(
        """
        <div style="text-align:center;padding:3rem 1rem;color:#94a3b8;">
            <div style="font-size:3rem;margin-bottom:0.5rem;">∞</div>
            <div style="font-size:1.1rem;font-weight:600;color:#64748b;">
                Your enterprise knowledge assistant is ready.
            </div>
            <div style="font-size:0.9rem;margin-top:0.5rem;">
                Ask a question about your ingested documents below.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ── Conversation replay ───────────────────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "user":
            st.markdown(msg["content"])
        else:
            # Render answer with styled citation markers
            formatted = _format_citations(msg["content"])
            st.markdown(
                f'<div class="answer-box">{formatted}</div>',
                unsafe_allow_html=True,
            )
            # Expandable sources section
            data = msg.get("data", {})
            matches = data.get("matches", [])
            if matches:
                with st.expander(f"📄 View {len(matches)} source chunk(s)"):
                    for i, match in enumerate(matches, 1):
                        score = match.get("score", 0)
                        source = match.get("source", "unknown")
                        text = match.get("text", "")
                        st.markdown(
                            f"**[{i}]** "
                            f'<span class="source-chip">{source}</span>'
                            f" · score: `{score:.4f}`",
                            unsafe_allow_html=True,
                        )
                        st.caption(text[:400] + ("…" if len(text) > 400 else ""))
                        if i < len(matches):
                            st.divider()

# ── RAG Verification Tour ────────────────────────────────────────────────────
_SUGGESTED = [
    (
        "📋 Test 1: Infrastructure Compliance updates",
        "give me a summary of the 2026 infrastructure standard compliance updates.",
    ),
    (
        "🗄️ Test 2: Core Storage & Indexing Policy",
        "knowledge_base_manifest",
    ),
    (
        "🚀 Test 3: Continuous Deployment Runbook",
        "what are the 2026 updates for routing and logging protocols?",
    ),
]

st.markdown(
    '<div class="tour-panel">'
    '<div class="tour-header">💡 Test the RAG Pipeline (Recommended Queries)</div>'
    "</div>",
    unsafe_allow_html=True,
)

_tour_cols = st.columns(3)
for _col, (_label, _query) in zip(_tour_cols, _SUGGESTED):
    with _col:
        if st.button(_label, use_container_width=True, key=f"tour_{_query[:20]}"):
            st.session_state.pending_query = _query
            st.rerun()

st.caption(
    "👉 **Tip:** Click a query to see **Live RAG Retrieval** (Blue Badge). "
    "Click it a **second time** to see the **~2ms Semantic Cache Hit** (Green Badge)!"
)

# ── Chat input ────────────────────────────────────────────────────────────────
_chat_input = st.chat_input("Ask Infinitum anything about your knowledge base…")

# Merge: a pending_query (from button click) takes priority over typed input.
# pending_query is consumed immediately so it never fires a second time.
_pending = st.session_state.pending_query
if _pending:
    st.session_state.pending_query = None
prompt = _pending or _chat_input

if prompt:
    # Record and display user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Call API
    with st.chat_message("assistant"):
        with st.spinner("Searching knowledge base and generating answer…"):
            result = _query_api(prompt, top_k=top_k)

        if result:
            answer = result.get("answer", "No answer returned.")
            formatted = _format_citations(answer)
            st.markdown(
                f'<div class="answer-box">{formatted}</div>',
                unsafe_allow_html=True,
            )

            matches = result.get("matches", [])
            if matches:
                with st.expander(f"📄 View {len(matches)} source chunk(s)"):
                    for i, match in enumerate(matches, 1):
                        score = match.get("score", 0)
                        source = match.get("source", "unknown")
                        text = match.get("text", "")
                        st.markdown(
                            f"**[{i}]** "
                            f'<span class="source-chip">{source}</span>'
                            f" · score: `{score:.4f}`",
                            unsafe_allow_html=True,
                        )
                        st.caption(text[:400] + ("…" if len(text) > 400 else ""))
                        if i < len(matches):
                            st.divider()

            # Persist message and telemetry
            st.session_state.messages.append(
                {"role": "assistant", "content": answer, "data": result}
            )
            st.session_state.last_telemetry = result
            st.rerun()
