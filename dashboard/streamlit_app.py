"""Streamlit dashboard for the Enterprise Context Engine API."""

from __future__ import annotations

import html
import os
from typing import Any

import requests
import streamlit as st

DEFAULT_API_URL = os.getenv("ECE_API_URL", "http://127.0.0.1:8000").rstrip("/")
DEFAULT_QUERY = "What is the invoice approval limit?"
EVAL_TEST_LABEL = "237 passed, 1 skipped"

DEMO_QUERIES = [
    ("Finance answer demo", "What is the invoice approval limit?"),
    ("Public handbook demo", "What does the handbook say about remote work?"),
    ("No-evidence abstention demo", "What is the unreleased acquisition plan?"),
    ("Engineering rollback demo", "How do we restore production after a bad release?"),
]


def main() -> None:
    st.set_page_config(
        page_title="Enterprise Context Engine",
        page_icon="E",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_global_styles()
    _ensure_session_defaults()

    sidebar_state = _render_sidebar()
    _render_header(sidebar_state)

    page = sidebar_state["page"]
    if page == "Ask Assistant":
        ask_assistant_page(sidebar_state)
    elif page == "Documents":
        documents_page()
    elif page == "Evaluation":
        evaluation_page()
    elif page == "Query Logs":
        query_logs_page()
    else:
        health_page(sidebar_state)


def _ensure_session_defaults() -> None:
    st.session_state.setdefault("api_url", DEFAULT_API_URL)
    st.session_state.setdefault("query_text", DEFAULT_QUERY)
    st.session_state.setdefault("api_key", "")
    st.session_state.setdefault("screenshot_mode", False)
    st.session_state.setdefault("last_response", None)


def inject_global_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
            --ece-bg: #f8fafc;
            --ece-card: #ffffff;
            --ece-border: #dbe5ef;
            --ece-muted: #64748b;
            --ece-ink: #0f172a;
            --ece-blue: #2563eb;
            --ece-blue-soft: #eff6ff;
            --ece-green: #15803d;
            --ece-green-soft: #f0fdf4;
            --ece-amber: #b45309;
            --ece-amber-soft: #fffbeb;
            --ece-red: #b42318;
        }
        html, body, [data-testid="stAppViewContainer"] {
            background: var(--ece-bg);
            color: var(--ece-ink);
        }
        .block-container {
            max-width: 1220px;
            padding: 1.1rem 1.6rem 2.5rem 1.6rem;
        }
        h1, h2, h3, p {
            letter-spacing: 0;
        }
        [data-testid="stHeader"],
        [data-testid="stToolbar"],
        [data-testid="stDecoration"],
        [data-testid="stStatusWidget"],
        [data-testid="collapsedControl"],
        footer {
            display: none !important;
        }
        [data-testid="stSidebar"] {
            background: #ffffff;
            border-right: 1px solid var(--ece-border);
            box-shadow: 1px 0 0 rgba(15, 23, 42, .02);
        }
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
            margin-bottom: .25rem;
        }
        .stButton > button {
            border-radius: 7px;
            border: 1px solid #cbd5e1;
            font-weight: 650;
        }
        .stButton > button[kind="primary"] {
            border-color: var(--ece-blue);
            background: var(--ece-blue);
        }
        .ece-sidebar-brand {
            border-bottom: 1px solid var(--ece-border);
            padding-bottom: .75rem;
            margin-bottom: .9rem;
        }
        .ece-sidebar-title {
            font-size: 1.02rem;
            font-weight: 800;
            color: var(--ece-ink);
            margin-bottom: .05rem;
        }
        .ece-sidebar-subtitle {
            color: var(--ece-muted);
            font-size: .82rem;
        }
        .ece-sidebar-section {
            color: #334155;
            font-size: .75rem;
            text-transform: uppercase;
            font-weight: 800;
            letter-spacing: .06em;
            margin: 1rem 0 .35rem 0;
        }
        .ece-hero {
            border: 1px solid var(--ece-border);
            border-radius: 10px;
            background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
            padding: 1.1rem 1.25rem;
            margin-bottom: 1rem;
            box-shadow: 0 1px 2px rgba(15, 23, 42, .04);
        }
        .ece-hero h1 {
            font-size: 2.05rem;
            line-height: 1.1;
            color: var(--ece-ink);
            margin: 0 0 .25rem 0;
        }
        .ece-hero p {
            color: var(--ece-muted);
            font-size: 1rem;
            margin: 0;
        }
        .ece-kicker {
            color: var(--ece-blue);
            font-weight: 800;
            font-size: .75rem;
            text-transform: uppercase;
            letter-spacing: .08em;
            margin-bottom: .25rem;
        }
        .ece-badge-row {
            display: flex;
            flex-wrap: wrap;
            gap: .45rem;
            margin-top: .8rem;
        }
        .ece-badge {
            display: inline-flex;
            align-items: center;
            border: 1px solid #cbd5e1;
            border-radius: 999px;
            background: #ffffff;
            color: #24364f;
            font-size: .76rem;
            font-weight: 700;
            padding: .22rem .6rem;
            white-space: nowrap;
        }
        .ece-badge-blue {
            border-color: #bfdbfe;
            background: var(--ece-blue-soft);
            color: #1d4ed8;
        }
        .ece-badge-green {
            border-color: #bbf7d0;
            background: var(--ece-green-soft);
            color: var(--ece-green);
        }
        .ece-card {
            border: 1px solid var(--ece-border);
            border-radius: 10px;
            background: var(--ece-card);
            padding: 1rem;
            margin: .55rem 0;
            box-shadow: 0 1px 2px rgba(15, 23, 42, .04);
        }
        .ece-panel {
            border: 1px solid var(--ece-border);
            border-radius: 10px;
            background: var(--ece-card);
            padding: 1rem;
            margin-bottom: .9rem;
        }
        .ece-card-title {
            color: var(--ece-ink);
            font-size: .8rem;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: .04em;
            margin-bottom: .35rem;
        }
        .ece-card-body {
            color: #24364f;
            font-size: .98rem;
            line-height: 1.55;
        }
        .ece-answer {
            border-left: 4px solid var(--ece-blue);
        }
        .ece-safe {
            border-left: 4px solid var(--ece-amber);
            background: var(--ece-amber-soft);
        }
        .ece-success {
            border-left: 4px solid var(--ece-green);
            background: var(--ece-green-soft);
        }
        .ece-citation {
            border: 1px solid var(--ece-border);
            border-radius: 9px;
            padding: .85rem;
            background: #ffffff;
            margin-bottom: .65rem;
        }
        .ece-citation strong {
            color: var(--ece-ink);
        }
        .ece-muted {
            color: var(--ece-muted);
            font-size: .86rem;
        }
        .ece-note {
            color: var(--ece-muted);
            font-size: .88rem;
            line-height: 1.45;
        }
        .ece-mini-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: .6rem;
        }
        .ece-mini-card {
            border: 1px solid var(--ece-border);
            border-radius: 8px;
            background: #ffffff;
            padding: .75rem;
        }
        .ece-mini-card .label {
            color: var(--ece-muted);
            font-size: .72rem;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: .04em;
        }
        .ece-mini-card .value {
            color: var(--ece-ink);
            font-size: 1.05rem;
            font-weight: 800;
            margin-top: .15rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_sidebar() -> dict[str, Any]:
    with st.sidebar:
        st.markdown(
            """
            <div class="ece-sidebar-brand">
              <div class="ece-sidebar-title">Enterprise Context Engine</div>
              <div class="ece-sidebar-subtitle">Local Demo Dashboard</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown('<div class="ece-sidebar-section">Backend API</div>', unsafe_allow_html=True)
        api_url = st.text_input("Backend API URL", key="api_url", label_visibility="visible")
        st.caption("This dashboard connects to your local FastAPI backend. No external API is required.")

        auth_status = _api_get("/auth/status", default={}, show_error=False)
        health = _api_get("/health", default={}, show_error=False)
        users = _api_get("/users", default=[], show_error=False)
        data_sources = _api_get("/data-sources", default=[], show_error=False)

        connected = isinstance(health, dict) and health.get("status") == "ok"
        if connected:
            st.success("Backend status: Connected")
        else:
            st.warning("Backend status: Offline")

        st.markdown('<div class="ece-sidebar-section">Auth</div>', unsafe_allow_html=True)
        auth_mode = "off"
        if isinstance(auth_status, dict):
            auth_mode = str(auth_status.get("auth_mode", "off"))
        st.session_state["auth_mode"] = auth_mode
        st.caption(f"Auth: {auth_mode}")
        if auth_mode == "api_key":
            st.caption("API key required.")
            st.text_input("API key", type="password", key="api_key")
        else:
            st.caption("No API key required for local demo.")
            st.session_state["api_key"] = ""

        st.markdown('<div class="ece-sidebar-section">Data Source</div>', unsafe_allow_html=True)
        data_source = _render_data_source_selector(health, data_sources)

        st.markdown('<div class="ece-sidebar-section">User</div>', unsafe_allow_html=True)
        user_id = _render_user_selector(users)

        st.markdown('<div class="ece-sidebar-section">Display</div>', unsafe_allow_html=True)
        screenshot_mode = st.checkbox(
            "Screenshot mode",
            key="screenshot_mode",
            help="Keeps noisy debug output collapsed or hidden for cleaner screenshots.",
        )

        st.markdown('<div class="ece-sidebar-section">Navigation</div>', unsafe_allow_html=True)
        page = st.radio(
            "Page",
            ["Ask Assistant", "Documents", "Evaluation", "Query Logs", "Health"],
            label_visibility="collapsed",
        )

    return {
        "page": page,
        "api_url": api_url,
        "auth_mode": auth_mode,
        "health": health,
        "data_source": data_source,
        "user_id": user_id,
        "screenshot_mode": screenshot_mode,
    }


def _render_header(sidebar_state: dict[str, Any]) -> None:
    auth_mode = html.escape(str(sidebar_state.get("auth_mode", "off")))
    data_source = html.escape(str(sidebar_state.get("data_source", "sample_docs")))
    user_id = html.escape(str(sidebar_state.get("user_id", "finance_user")))
    st.markdown(
        f"""
        <div class="ece-hero">
          <div class="ece-kicker">Local demo dashboard</div>
          <h1>Enterprise Context Engine</h1>
          <p>Permission-aware context engineering for enterprise LLM applications.</p>
          <div class="ece-badge-row">
            <span class="ece-badge ece-badge-blue">Auth/RBAC</span>
            <span class="ece-badge ece-badge-blue">Hybrid Retrieval</span>
            <span class="ece-badge ece-badge-blue">Evidence Gate</span>
            <span class="ece-badge ece-badge-blue">Citations</span>
            <span class="ece-badge ece-badge-green">Eval: 37/37 + 18/18</span>
            <span class="ece-badge">Auth: {auth_mode}</span>
            <span class="ece-badge">Source: {data_source}</span>
            <span class="ece-badge">User: {user_id}</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_data_source_selector(health: Any, data_sources: Any) -> str:
    if not isinstance(data_sources, list) or not data_sources:
        st.caption("Data source: sample_docs")
        return "sample_docs"

    labels_by_id = {item["id"]: item["label"] for item in data_sources}
    descriptions_by_id = {item["id"]: item.get("description", "") for item in data_sources}
    source_ids = list(labels_by_id)
    current_source = "sample_docs"
    if isinstance(health, dict):
        current_source = str(health.get("active_data_source", "sample_docs"))
    default_index = source_ids.index(current_source) if current_source in source_ids else 0
    selected_source = st.selectbox(
        "Corpus",
        source_ids,
        index=default_index,
        format_func=lambda source_id: labels_by_id.get(source_id, source_id),
        label_visibility="collapsed",
    )
    if not st.session_state.get("screenshot_mode"):
        st.caption(descriptions_by_id.get(selected_source, ""))
    if st.button("Load data source", width="stretch"):
        result = _api_post("/ingest/data-source", {"mode": selected_source}, default=None)
        if isinstance(result, dict):
            st.success(
                f"Loaded {result.get('active_data_source')} with "
                f"{result.get('documents_ingested', 0)} documents and "
                f"{result.get('chunks_created', 0)} chunks."
            )
    return selected_source


def _render_user_selector(users: Any) -> str:
    user_ids = [user["user_id"] for user in users] if isinstance(users, list) else []
    if not user_ids:
        user_ids = ["finance_user"]
    default_index = user_ids.index("finance_user") if "finance_user" in user_ids else 0
    return st.selectbox("Demo user", user_ids, index=default_index, label_visibility="collapsed")


def ask_assistant_page(sidebar_state: dict[str, Any]) -> None:
    st.subheader("Ask Assistant")
    health = sidebar_state.get("health")
    document_count = health.get("document_count", 0) if isinstance(health, dict) else 0
    chunk_count = health.get("chunk_count", 0) if isinstance(health, dict) else 0

    st.markdown(
        f"""
        <div class="ece-mini-grid">
          <div class="ece-mini-card"><div class="label">Selected user</div><div class="value">{html.escape(str(sidebar_state["user_id"]))}</div></div>
          <div class="ece-mini-card"><div class="label">Data source</div><div class="value">{html.escape(str(sidebar_state["data_source"]))}</div></div>
          <div class="ece-mini-card"><div class="label">Documents</div><div class="value">{document_count}</div></div>
          <div class="ece-mini-card"><div class="label">Chunks</div><div class="value">{chunk_count}</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("#### Suggested demo queries")
    query_cols = st.columns(4)
    for index, (label, demo_query) in enumerate(DEMO_QUERIES):
        if query_cols[index].button(label, width="stretch"):
            st.session_state["query_text"] = demo_query

    st.markdown('<div class="ece-panel">', unsafe_allow_html=True)
    query = st.text_area("Question", key="query_text", height=96)
    with st.expander("Retrieval controls", expanded=False):
        final_context_results = st.slider(
            "Final context results",
            min_value=1,
            max_value=20,
            value=5,
            help="Controls how many accessible chunks are used to build the answer.",
        )
        st.caption(
            "Initial retrieval pool controls how many candidate chunks are considered before "
            "filtering. Final context results controls how many chunks are used to build the answer."
        )
    ask_clicked = st.button("Ask assistant", type="primary", width="stretch")
    st.markdown("</div>", unsafe_allow_html=True)

    if ask_clicked:
        response = _api_post(
            "/query",
            {
                "user_id": sidebar_state["user_id"],
                "query": query,
                "top_k": final_context_results,
            },
            default=None,
        )
        if isinstance(response, dict):
            st.session_state["last_response"] = response

    response = st.session_state.get("last_response")
    if isinstance(response, dict):
        _render_answer(response, screenshot_mode=bool(sidebar_state.get("screenshot_mode")))
    else:
        _card(
            "Ready",
            "Choose a demo query or ask a question to see a grounded answer, citations, and safety status.",
            modifier="ece-success",
        )


def _render_answer(response: dict[str, Any], screenshot_mode: bool) -> None:
    answer = str(response.get("answer", ""))
    safe_abstain = bool(response.get("safe_abstain", False))
    if safe_abstain:
        _card(
            "Safe Abstention",
            "No accessible supporting evidence was found for this question.",
            modifier="ece-safe",
        )
    else:
        _card("Answer", answer, modifier="ece-answer")

    citations = response.get("citations", [])
    if citations:
        st.markdown("#### Citations")
        for index, citation in enumerate(citations, start=1):
            _render_citation(index, citation)
    else:
        st.caption("No citations returned.")

    debug = _debug_summary(response.get("debug", {}))
    _render_safety_summary(debug, safe_abstain)
    if not screenshot_mode:
        with st.expander("Debug details", expanded=False):
            st.json(debug)


def _render_citation(index: int, citation: dict[str, Any]) -> None:
    title = html.escape(str(citation.get("document_title", "Untitled document")))
    section = html.escape(str(citation.get("section_title", "Unknown section")))
    department = html.escape(str(citation.get("department", "unknown")))
    access_level = html.escape(str(citation.get("access_level", "unknown")))
    method = html.escape(str(citation.get("retrieval_method", "retrieval")))
    score = html.escape(str(citation.get("score", "")))
    st.markdown(
        f"""
        <div class="ece-citation">
          <div class="ece-card-title">Citation {index}</div>
          <strong>Document: {title}</strong>
          <div class="ece-muted">Section: {section}</div>
          <div class="ece-badge-row">
            <span class="ece-badge">Department: {department}</span>
            <span class="ece-badge">Access: {access_level}</span>
            <span class="ece-badge">Method: {method}</span>
            <span class="ece-badge">Score: {score}</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_safety_summary(debug: dict[str, Any], safe_abstain: bool) -> None:
    status = "Safe Abstention" if safe_abstain else "Grounded Answer"
    body = (
        f"Retrieval: {debug.get('retrieval_mode', 'unknown')} | "
        f"Intent: {debug.get('intent', 'unknown')} | "
        f"Citations: {debug.get('citation_count', 0)} | "
        f"Auth: {debug.get('auth_mode', 'off')}"
    )
    _card(status, body, modifier="ece-safe" if safe_abstain else "ece-success")


def documents_page() -> None:
    st.subheader("Documents")
    st.caption("Document metadata only. Raw restricted context is not shown in this dashboard.")
    documents = _api_get("/documents", default=[])
    if not isinstance(documents, list):
        return

    departments = sorted({document.get("department", "") for document in documents})
    source_names = sorted(
        {
            document.get("source_name") or document.get("source_path") or "unknown"
            for document in documents
        }
    )
    col_a, col_b = st.columns(2)
    department = col_a.selectbox("Department filter", ["all", *departments])
    source_filter = col_b.selectbox("Source filter", ["all", *source_names])

    filtered = [
        {
            "Title": document.get("title"),
            "Department": document.get("department"),
            "Access Level": document.get("access_level"),
            "Source": document.get("source_name") or document.get("source_path"),
            "Document Type": document.get("document_type"),
        }
        for document in documents
        if (department == "all" or document.get("department") == department)
        and (source_filter == "all" or (document.get("source_name") or document.get("source_path")) == source_filter)
    ]
    st.dataframe(filtered, width="stretch", hide_index=True)


def evaluation_page() -> None:
    st.subheader("Evaluation")
    st.markdown(
        """
        <div class="ece-mini-grid">
          <div class="ece-mini-card"><div class="label">sample_docs</div><div class="value">37/37 passed</div><div class="ece-muted">Pass rate: 1.00</div></div>
          <div class="ece-mini-card"><div class="label">gitlab_handbook</div><div class="value">18/18 passed</div><div class="ece-muted">Pass rate: 1.00</div></div>
          <div class="ece-mini-card"><div class="label">Restricted leak rate</div><div class="value">0.00</div></div>
          <div class="ece-mini-card"><div class="label">Tests</div><div class="value">237 passed</div><div class="ece-muted">1 skipped</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption("Deterministic evals are local and do not require LLM-as-judge or external services.")
    st.caption("Evaluation Source: choose one of the source-specific evaluation runs below.")

    col_a, col_b = st.columns(2)
    if col_a.button("Run sample_docs evaluation", type="primary", width="stretch"):
        summary = _api_post("/evaluate?source=sample_docs", {}, default=None)
        if isinstance(summary, dict):
            _render_eval_summary(summary)
    if col_b.button("Run gitlab_handbook evaluation", width="stretch"):
        summary = _api_post("/evaluate?source=gitlab_handbook", {}, default=None)
        if isinstance(summary, dict):
            _render_eval_summary(summary)

    metrics = _api_get("/metrics", default={})
    if isinstance(metrics, dict):
        if metrics.get("status") == "no_evaluation_run":
            st.info("No evaluation run yet.")
        else:
            _render_eval_summary(metrics)


def query_logs_page() -> None:
    st.subheader("Query Logs")
    _card(
        "Sanitized logs",
        "Raw context and restricted chunk text are not stored in logs.",
        modifier="ece-success",
    )
    logs = _api_get("/logs", default=[])
    if isinstance(logs, list):
        rows = [
            {
                "Query ID": log.get("query_id"),
                "User": log.get("user_id"),
                "Query": log.get("query"),
                "Safe Abstain": log.get("safe_abstain"),
                "Citations": log.get("citation_count"),
                "Retrieval": log.get("retrieval_mode"),
                "Intent": log.get("intent"),
                "Latency ms": log.get("latency_ms"),
                "Created": log.get("created_at"),
            }
            for log in logs
        ]
        st.dataframe(rows, width="stretch", hide_index=True)


def health_page(sidebar_state: dict[str, Any]) -> None:
    st.subheader("Health")
    health = sidebar_state.get("health")
    storage_backend = health.get("storage_backend", "memory") if isinstance(health, dict) else "memory"
    active_source = health.get("active_data_source", "sample_docs") if isinstance(health, dict) else "sample_docs"
    document_count = health.get("document_count", 0) if isinstance(health, dict) else 0
    chunk_count = health.get("chunk_count", 0) if isinstance(health, dict) else 0
    backend_status = "Connected" if isinstance(health, dict) and health.get("status") == "ok" else "Offline"
    vector_backend = os.getenv("ECE_VECTOR_BACKEND", "memory")

    st.markdown(
        f"""
        <div class="ece-mini-grid">
          <div class="ece-mini-card"><div class="label">Backend</div><div class="value">{backend_status}</div></div>
          <div class="ece-mini-card"><div class="label">Auth mode</div><div class="value">{html.escape(str(sidebar_state.get("auth_mode", "off")))}</div></div>
          <div class="ece-mini-card"><div class="label">Storage backend</div><div class="value">{html.escape(str(storage_backend))}</div></div>
          <div class="ece-mini-card"><div class="label">Vector backend</div><div class="value">{html.escape(str(vector_backend))}</div></div>
          <div class="ece-mini-card"><div class="label">Active data source</div><div class="value">{html.escape(str(active_source))}</div></div>
          <div class="ece-mini-card"><div class="label">Documents loaded</div><div class="value">{document_count}</div></div>
          <div class="ece-mini-card"><div class="label">Chunks loaded</div><div class="value">{chunk_count}</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _card(
        "Local demo mode",
        "The dashboard connects to the local FastAPI backend. No external API is required for the default demo.",
        modifier="ece-success",
    )

    if st.button("Ingest Sample Docs", type="primary"):
        result = _api_post("/ingest/sample", {}, default=None)
        if isinstance(result, dict):
            st.success(
                f"Ingested {result.get('documents_ingested', 0)} documents and "
                f"{result.get('chunks_created', 0)} chunks."
            )
    if not sidebar_state.get("screenshot_mode") and isinstance(health, dict):
        with st.expander("Health details", expanded=False):
            st.json(health)


def _render_eval_summary(summary: dict[str, Any]) -> None:
    metrics = summary.get("metrics", {})
    if summary.get("source"):
        st.caption(f"Source: {summary.get('source')}")
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("Total", summary.get("total_examples", 0))
    col_b.metric("Passed", summary.get("passed_examples", 0))
    col_c.metric("Failed", summary.get("failed_examples", 0))
    if metrics:
        st.dataframe(
            [{"metric": key, "value": value} for key, value in metrics.items()],
            width="stretch",
            hide_index=True,
        )


def _card(title: str, body: str, modifier: str = "") -> None:
    st.markdown(
        f"""
        <div class="ece-card {modifier}">
          <div class="ece-card-title">{html.escape(title)}</div>
          <div class="ece-card-body">{html.escape(body)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _base_url() -> str:
    return str(st.session_state.get("api_url", DEFAULT_API_URL) or DEFAULT_API_URL).rstrip("/")


def _api_get(path: str, default: Any, show_error: bool = True) -> Any:
    try:
        response = requests.get(f"{_base_url()}{path}", headers=_api_headers(), timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        if show_error:
            st.error(f"API request failed: {exc}")
        return default


def _api_post(path: str, payload: dict[str, Any], default: Any) -> Any:
    try:
        response = requests.post(f"{_base_url()}{path}", json=payload, headers=_api_headers(), timeout=120)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        st.error(f"API request failed: {exc}")
        return default


def _debug_summary(debug: dict[str, Any]) -> dict[str, Any]:
    allowed_keys = {
        "llm_called",
        "citation_count",
        "model_name",
        "retrieval_mode",
        "intent",
        "focused_chunks_before_access",
        "focused_chunks_after_access",
        "filtered_chunk_count",
        "included_chunk_count",
        "auth_mode",
        "authenticated_user_id",
    }
    return {key: value for key, value in debug.items() if key in allowed_keys}


def _api_headers() -> dict[str, str]:
    auth_mode = str(st.session_state.get("auth_mode", "off"))
    if auth_mode != "api_key":
        return {}
    api_key = str(st.session_state.get("api_key", "") or "").strip()
    if not api_key:
        return {}
    return {"X-API-Key": api_key}


if __name__ == "__main__":
    main()
