"""
Infinitum AI — Premium studio-grade chat interface.

Run with:
    streamlit run app/ui.py

Requires the FastAPI server to be running:
    uvicorn app.main:app --reload
"""

import re
import requests
import streamlit as st

import os
API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000")
DEFAULT_TOP_K = 5

# ── Page config (must be first Streamlit call) ────────────────────────────────
st.set_page_config(
    page_title="Infinitum AI",
    page_icon="∞",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Premium Design System ─────────────────────────────────────────────────────
st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;600&display=swap');

        :root {
            --brand-primary: #6C5CE7;
            --brand-primary-light: #A29BFE;
            --brand-accent: #00CEC9;
            --brand-accent-2: #FD79A8;
            --surface-0: #0A0A0F;
            --surface-1: #12121A;
            --surface-2: #1A1A26;
            --surface-3: #22222E;
            --border-subtle: rgba(255,255,255,0.06);
            --border-medium: rgba(255,255,255,0.1);
            --text-primary: #F0F0F5;
            --text-secondary: #9494A8;
            --text-tertiary: #5E5E72;
            --glow-brand: 0 0 30px rgba(108,92,231,0.3);
            --glow-accent: 0 0 20px rgba(0,206,201,0.2);
        }

        html, body, [class*="css"] {
            font-family: "Inter", -apple-system, BlinkMacSystemFont, sans-serif;
            background: var(--surface-0) !important;
            color: var(--text-primary) !important;
        }

        .stApp {
            background: var(--surface-0) !important;
        }

        .stApp > header { background-color: transparent !important; }
        .stApp > footer { display: none !important; }
        #MainMenu, footer, header { visibility: hidden; }

        /* ---- Sidebar glass ---- */
        section[data-testid="stSidebar"] {
            background: var(--surface-1) !important;
            border-right: 1px solid var(--border-subtle) !important;
        }
        section[data-testid="stSidebar"] > div {
            background: transparent !important;
        }

        /* ---- Scrollbar ---- */
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: var(--surface-3); border-radius: 3px; }
        ::-webkit-scrollbar-thumb:hover { background: var(--text-tertiary); }

        /* ---- Hero ---- */
        .hero-container {
            position: relative;
            padding: 2.5rem 0 1.5rem;
            overflow: hidden;
        }
        .hero-container::before {
            content: '';
            position: absolute; inset: 0;
            background: radial-gradient(ellipse 60% 50% at 50% 0%, rgba(108,92,231,0.15), transparent),
                        radial-gradient(ellipse 40% 40% at 80% 20%, rgba(0,206,201,0.08), transparent);
            pointer-events: none;
        }
        .hero-inner {
            position: relative;
            display: flex; align-items: center; gap: 16px;
        }
        .hero-logo {
            font-size: 2.8rem; font-weight: 900;
            background: linear-gradient(135deg, var(--brand-primary), var(--brand-accent));
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            filter: drop-shadow(0 0 20px rgba(108,92,231,0.4));
            line-height: 1;
        }
        .hero-title {
            font-size: 1.5rem; font-weight: 800;
            color: var(--text-primary);
            letter-spacing: -0.02em;
        }
        .hero-badge {
            display: inline-flex; align-items: center; gap: 6px;
            background: rgba(108,92,231,0.12);
            border: 1px solid rgba(108,92,231,0.25);
            color: var(--brand-primary-light);
            border-radius: 999px; padding: 3px 12px;
            font-size: 0.7rem; font-weight: 600;
            letter-spacing: 0.08em; text-transform: uppercase;
            margin-left: 10px;
        }
        .hero-subtitle {
            font-size: 0.88rem; color: var(--text-secondary);
            margin-top: 4px; font-weight: 400;
        }
        .hero-dot {
            display: inline-block; width: 6px; height: 6px;
            border-radius: 50%; margin: 0 8px;
            vertical-align: middle;
        }
        .dot-pinecone { background: #00CEC9; box-shadow: 0 0 6px rgba(0,206,201,0.5); }
        .dot-llama { background: #6C5CE7; box-shadow: 0 0 6px rgba(108,92,231,0.5); }
        .dot-redis { background: #FD79A8; box-shadow: 0 0 6px rgba(253,121,168,0.5); }
        .dot-nvidia { background: #76B900; box-shadow: 0 0 6px rgba(118,185,0,0.5); }

        /* ---- Welcome state ---- */
        .welcome-container {
            text-align: center;
            padding: 4rem 1rem 2rem;
        }
        .welcome-icon {
            width: 80px; height: 80px;
            margin: 0 auto 1.5rem;
            border-radius: 24px;
            background: linear-gradient(135deg, rgba(108,92,231,0.15), rgba(0,206,201,0.1));
            border: 1px solid var(--border-medium);
            display: flex; align-items: center; justify-content: center;
            font-size: 2.2rem;
            box-shadow: var(--glow-brand);
            animation: float 3s ease-in-out infinite;
        }
        @keyframes float {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-8px); }
        }
        .welcome-heading {
            font-size: 1.3rem; font-weight: 700;
            color: var(--text-primary);
            margin-bottom: 0.5rem;
        }
        .welcome-desc {
            font-size: 0.92rem; color: var(--text-secondary);
            line-height: 1.6; max-width: 480px; margin: 0 auto;
        }

        /* ---- Test cards ---- */
        .test-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 12px;
            margin: 2rem 0 0.8rem;
        }
        .test-card {
            background: var(--surface-1);
            border: 1px solid var(--border-subtle);
            border-radius: 14px;
            padding: 1.1rem 1rem;
            transition: all 0.25s ease;
            cursor: pointer;
        }
        .test-card:hover {
            border-color: rgba(108,92,231,0.3);
            background: var(--surface-2);
            box-shadow: 0 4px 20px rgba(108,92,231,0.1);
            transform: translateY(-1px);
        }
        .test-card-number {
            font-size: 0.65rem; font-weight: 700;
            color: var(--brand-primary-light);
            letter-spacing: 0.1em; text-transform: uppercase;
            margin-bottom: 0.5rem;
        }
        .test-card-icon {
            font-size: 1.4rem;
            margin-bottom: 0.5rem;
        }
        .test-card-title {
            font-size: 0.82rem; font-weight: 600;
            color: var(--text-primary);
            line-height: 1.4;
        }
        .tip-text {
            font-size: 0.75rem; color: var(--text-tertiary);
            line-height: 1.5;
            text-align: center;
            margin-top: 0.25rem;
        }
        .tip-highlight { color: var(--brand-primary-light); font-weight: 600; }

        /* ---- Answer box ---- */
        .answer-box {
            background: var(--surface-1);
            border: 1px solid var(--border-subtle);
            border-left: 3px solid var(--brand-primary);
            border-radius: 0 14px 14px 0;
            padding: 1.2rem 1.4rem;
            line-height: 1.75; color: var(--text-primary);
            font-size: 0.95rem;
        }

        /* ---- Cite markers ---- */
        .cite {
            display: inline-flex; align-items: center; justify-content: center;
            min-width: 20px; height: 20px; padding: 0 5px;
            background: linear-gradient(135deg, var(--brand-primary), #8B5CF6);
            color: white; border-radius: 10px;
            font-size: 0.65rem; font-weight: 700;
            vertical-align: super; margin: 0 2px;
            box-shadow: 0 2px 8px rgba(108,92,231,0.3);
        }

        /* ---- Source chips ---- */
        .source-chip {
            display: inline-block;
            background: rgba(108,92,231,0.1);
            border: 1px solid rgba(108,92,231,0.2);
            color: var(--brand-primary-light);
            border-radius: 8px; padding: 3px 10px;
            font-size: 0.72rem; font-weight: 500;
            margin: 2px 4px 2px 0;
        }

        /* ---- Sidebar: Brand ---- */
        .sidebar-brand {
            padding: 0.5rem 0 0;
        }
        .sidebar-logo {
            font-size: 1.8rem; font-weight: 900;
            background: linear-gradient(135deg, var(--brand-primary), var(--brand-accent));
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            line-height: 1;
        }
        .sidebar-tagline {
            font-size: 0.72rem; color: var(--text-tertiary);
            letter-spacing: 0.05em; text-transform: uppercase;
            font-weight: 600; margin-top: 4px;
        }

        /* ---- Sidebar: Telemetry ---- */
        .badge {
            display: flex; align-items: center; justify-content: center; gap: 8px;
            padding: 10px 16px; border-radius: 12px;
            font-size: 0.75rem; font-weight: 700;
            letter-spacing: 0.06em; text-transform: uppercase;
            width: 100%; margin: 0 0 1rem;
        }
        .badge-cache {
            background: rgba(0,206,201,0.1);
            color: #00CEC9;
            border: 1px solid rgba(0,206,201,0.25);
        }
        .badge-live {
            background: rgba(108,92,231,0.1);
            color: var(--brand-primary-light);
            border: 1px solid rgba(108,92,231,0.25);
        }
        .badge-intent {
            background: rgba(253,121,168,0.1);
            color: #FD79A8;
            border: 1px solid rgba(253,121,168,0.25);
        }
        .badge-dot {
            width: 8px; height: 8px; border-radius: 50%;
            animation: pulse-dot 2s ease-in-out infinite;
        }
        .badge-cache .badge-dot { background: #00CEC9; box-shadow: 0 0 8px rgba(0,206,201,0.6); }
        .badge-live .badge-dot { background: var(--brand-primary-light); box-shadow: 0 0 8px rgba(108,92,231,0.6); }
        .badge-intent .badge-dot { background: #FD79A8; box-shadow: 0 0 8px rgba(253,121,168,0.6); }
        @keyframes pulse-dot {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.5; transform: scale(0.8); }
        }

        .metric-row { display: flex; gap: 8px; margin-bottom: 0.6rem; }
        .metric-card {
            flex: 1;
            background: var(--surface-2);
            border: 1px solid var(--border-subtle);
            border-radius: 10px; padding: 12px 10px; text-align: center;
        }
        .metric-label {
            font-size: 0.62rem; color: var(--text-tertiary);
            text-transform: uppercase; letter-spacing: 0.08em;
            font-weight: 600;
        }
        .metric-value {
            font-size: 1.2rem; font-weight: 800;
            color: var(--text-primary);
            margin-top: 4px;
            font-family: "JetBrains Mono", monospace;
        }

        /* ---- Sidebar: Clear button ---- */
        .sidebar-clear button {
            background: var(--surface-2) !important;
            border: 1px solid var(--border-medium) !important;
            color: var(--text-secondary) !important;
            border-radius: 10px !important;
            font-weight: 600 !important;
            font-size: 0.82rem !important;
            transition: all 0.2s ease !important;
        }
        .sidebar-clear button:hover {
            border-color: rgba(253,121,168,0.4) !important;
            color: #FD79A8 !important;
            background: rgba(253,121,168,0.08) !important;
        }

        /* ---- Chat input ---- */
        .stChatInputContainer {
            padding-top: 0.5rem;
        }
        .stChatInputContainer > div {
            border-radius: 16px !important;
            border: 1px solid var(--border-medium) !important;
            background: var(--surface-1) !important;
        }

        /* ---- Chat messages ---- */
        [data-testid="stChatMessage"] {
            background: transparent !important;
            border: none !important;
            padding: 0.5rem 0 !important;
        }
        [data-testid="stChatMessageAvatar-Assistant"] {
            background: linear-gradient(135deg, var(--brand-primary), var(--brand-accent)) !important;
        }

        /* ---- Expander ---- */
        .streamlit-expanderHeader {
            font-size: 0.82rem !important;
            font-weight: 600 !important;
            color: var(--text-secondary) !important;
            background: var(--surface-1) !important;
            border: 1px solid var(--border-subtle) !important;
            border-radius: 12px !important;
        }

        /* ---- Slider ---- */
        .stSlider label {
            font-size: 0.82rem !important;
            font-weight: 600 !important;
            color: var(--text-secondary) !important;
        }

        /* ---- Section divider ---- */
        .section-divider {
            height: 1px;
            background: linear-gradient(90deg, transparent, var(--border-medium), transparent);
            margin: 1rem 0;
        }

        /* ---- Status bar (bottom of sidebar) ---- */
        .status-bar {
            display: flex; align-items: center; gap: 8px;
            padding: 0.75rem 0; margin-top: 0.5rem;
        }
        .status-dot {
            width: 8px; height: 8px; border-radius: 50%;
            background: #00CEC9;
            box-shadow: 0 0 8px rgba(0,206,201,0.5);
        }
        .status-text {
            font-size: 0.72rem; color: var(--text-tertiary);
            font-weight: 500;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ── Helper functions ──────────────────────────────────────────────────────────

def _format_citations(text: str) -> str:
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
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.Timeout:
        st.error("The API timed out after 30 seconds. The server may be overloaded — please try again.")
        return None
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
    retrieval = latency.get("retrieval_ms", 0.0)
    generation = latency.get("generation_ms", 0.0)
    is_zero_latency = (retrieval == 0.0 and generation == 0.0)

    if cache_hit:
        st.sidebar.markdown(
            '<div class="badge badge-cache"><span class="badge-dot"></span>Cache Hit (Redis)</div>',
            unsafe_allow_html=True,
        )
    elif is_zero_latency:
        st.sidebar.markdown(
            '<div class="badge badge-intent"><span class="badge-dot"></span>Intent Router Bypass</div>',
            unsafe_allow_html=True,
        )
    else:
        st.sidebar.markdown(
            '<div class="badge badge-live"><span class="badge-dot"></span>Live Pipeline Generation</div>',
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
                <div class="metric-value">{retrieval:.0f}<span style="font-size:0.6rem;color:var(--text-tertiary)">ms</span></div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Generation</div>
                <div class="metric-value">{generation:.0f}<span style="font-size:0.6rem;color:var(--text-tertiary)">ms</span></div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Total</div>
                <div class="metric-value">{total:.0f}<span style="font-size:0.6rem;color:var(--text-tertiary)">ms</span></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Session state ─────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

if "last_telemetry" not in st.session_state:
    st.session_state.last_telemetry = None

if "pending_query" not in st.session_state:
    st.session_state.pending_query = None


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        """
        <div class="sidebar-brand">
            <div class="sidebar-logo">∞ Infinitum</div>
            <div class="sidebar-tagline">Enterprise RAG Platform</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    top_k = st.slider(
        "Chunks to retrieve (top_k)",
        min_value=1, max_value=20, value=DEFAULT_TOP_K,
    )

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    with st.expander("Developer Telemetry", expanded=True):
        if st.session_state.last_telemetry:
            data = st.session_state.last_telemetry
            _render_telemetry(
                latency=data.get("latency_ms", {}),
                cache_hit=data.get("cache_hit", False),
            )
            match_count = data.get("match_count", 0)
            st.caption(f"Context chunks used: **{match_count}**")
        else:
            st.info("Telemetry will appear after your first query.", icon="📊")

    st.markdown('<div class="section-divider"></div>', unsafe_allow_html=True)

    st.markdown('<div class="sidebar-clear">', unsafe_allow_html=True)
    if st.button("Clear conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.last_telemetry = None
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown(
        """
        <div class="status-bar">
            <div class="status-dot"></div>
            <div class="status-text">Systems operational</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Hero header ───────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="hero-container">
        <div class="hero-inner">
            <div class="hero-logo">∞</div>
            <div>
                <div style="display:flex;align-items:center;">
                    <span class="hero-title">Infinitum AI</span>
                    <span class="hero-badge">● Live</span>
                </div>
                <div class="hero-subtitle">
                    Pinecone
                    <span class="hero-dot dot-pinecone"></span>
                    Llama 3.1 8B
                    <span class="hero-dot dot-nvidia"></span>
                    Llama 3
                    <span class="hero-dot dot-llama"></span>
                    Redis
                    <span class="hero-dot dot-redis"></span>
                </div>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Welcome state ─────────────────────────────────────────────────────────────
if not st.session_state.messages:
    st.markdown(
        """
        <div class="welcome-container">
            <div class="welcome-icon">∞</div>
            <div class="welcome-heading">Your enterprise knowledge assistant is ready</div>
            <div class="welcome-desc">
                Ask questions about your ingested documents, or try the recommended queries below to see the RAG pipeline in action.
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
            formatted = _format_citations(msg["content"])
            st.markdown(
                f'<div class="answer-box">{formatted}</div>',
                unsafe_allow_html=True,
            )
            data = msg.get("data", {})
            matches = data.get("matches", [])
            if matches:
                with st.expander(f"View {len(matches)} source chunk(s)"):
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
                        st.caption(text[:400] + ("..." if len(text) > 400 else ""))
                        if i < len(matches):
                            st.divider()

# ── Test cards ────────────────────────────────────────────────────────────────
_SUGGESTED = [
    ("TEST 01", "📋", "Infrastructure compliance updates", "give me a summary of the 2026 infrastructure standard compliance updates."),
    ("TEST 02", "🗄️", "Core storage & indexing policy", "knowledge_base_manifest"),
    ("TEST 03", "🚀", "Continuous deployment runbook", "what are the 2026 updates for routing and logging protocols?"),
]

if not st.session_state.messages:
    _cols = st.columns(3)
    for _col, (_num, _icon, _title, _query) in zip(_cols, _SUGGESTED):
        with _col:
            if st.button(
                f"{_icon}  {_title}",
                use_container_width=True,
                key=f"tour_{_query[:20]}",
            ):
                st.session_state.pending_query = _query
                st.rerun()

    st.markdown(
        '<div class="tip-text">'
        '<span class="tip-highlight">Tip:</span> Click once for '
        '<span style="color:#6C5CE7">Live RAG</span>, click again for '
        '<span style="color:#00CEC9">~2ms Cache Hit</span>'
        '</div>',
        unsafe_allow_html=True,
    )

# ── Chat input ────────────────────────────────────────────────────────────────
_chat_input = st.chat_input("Ask Infinitum anything about your knowledge base...")

_pending = st.session_state.pending_query
if _pending:
    st.session_state.pending_query = None
    prompt = _pending or _chat_input
else:
    prompt = _chat_input

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Searching knowledge base..."):
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
                with st.expander(f"View {len(matches)} source chunk(s)"):
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
                        st.caption(text[:400] + ("..." if len(text) > 400 else ""))
                        if i < len(matches):
                            st.divider()

            st.session_state.messages.append(
                {"role": "assistant", "content": answer, "data": result}
            )
            st.session_state.last_telemetry = result
            st.rerun()
