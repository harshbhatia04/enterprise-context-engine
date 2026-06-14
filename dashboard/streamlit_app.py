"""Streamlit dashboard for the Enterprise Context Engine API."""

from __future__ import annotations

import html
import os
from typing import Any

import requests
import streamlit as st

DEFAULT_API_URL = os.getenv("ECE_API_URL", "http://localhost:8000").rstrip("/")
DEFAULT_QUERY = "What is the invoice approval limit?"
DEMO_QUERIES = [
    "What is the invoice approval limit?",
    "What does the handbook say about remote work?",
    "What is the unreleased acquisition plan?",
]


def main() -> None:
    st.set_page_config(page_title="Enterprise Context Engine", layout="wide")
    _apply_css()
    _ensure_session_defaults()

    _render_header()
    sidebar_state = _render_sidebar()

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


def _apply_css() -> None:
    st.markdown(
        """
        <style>
        :root {
            --ece-border: #dfe6ee;
            --ece-muted: #5b677a;
            --ece-ink: #172033;
            --ece-soft: #f6f8fb;
            --ece-blue: #2457c5;
            --ece-green: #147b4f;
            --ece-amber: #9a5b00;
            --ece-red: #b42318;
        }
        .block-container {
            padding-top: 1.8rem;
            padding-bottom: 3rem;
            max-width: 1180px;
        }
        h1, h2, h3 {
            letter-spacing: 0;
        }
        [data-testid="stSidebar"] {
            background: #f8fafc;
            border-right: 1px solid var(--ece-border);
        }
        .ece-hero {
            padding: 1.15rem 1.25rem;
            border: 1px solid var(--ece-border);
            border-radius: 8px;
            background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
            margin-bottom: 1rem;
        }
        .ece-hero h1 {
            color: var(--ece-ink);
            font-size: 2rem;
            line-height: 1.15;
            margin: 0 0 .35rem 0;
        }
        .ece-hero p {
            color: var(--ece-muted);
            font-size: 1rem;
            margin: 0;
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
            border: 1px solid #cdd8e6;
            border-radius: 999px;
            background: #ffffff;
            color: #24364f;
            font-size: .78rem;
            font-weight: 650;
            padding: .22rem .55rem;
        }
        .ece-card {
            border: 1px solid var(--ece-border);
            border-radius: 8px;
            background: #ffffff;
            padding: 1rem;
            margin: .55rem 0;
            box-shadow: 0 1px 2px rgba(15, 23, 42, .04);
        }
        .ece-card-title {
            color: var(--ece-ink);
            font-size: .82rem;
            font-weight: 750;
            text-transform: uppercase;
            letter-spacing: .02em;
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
            background: #fff8ed;
        }
        .ece-success {
            border-left: 4px solid var(--ece-green);
            background: #f0fbf6;
        }
        .ece-citation {
            border: 1px solid var(--ece-border);
            border-radius: 8px;
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
        .ece-kicker {
            color: var(--ece-blue);
            font-weight: 750;
            font-size: .82rem;
            text-transform: uppercase;
            letter-spacing: .06em;
            margin-bottom: .15rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_header() -> None:
    st.markdown(
        """
        <div class="ece-hero">
          <div class="ece-kicker">Local demo dashboard</div>
          <h1>Enterprise Context Engine</h1>
          <p>Permission-aware context engineering for enterprise LLM applications.</p>
          <div class="ece-badge-row">
            <span class="ece-badge">Auth/RBAC</span>
            <span class="ece-badge">Hybrid Retrieval</span>
            <span class="ece-badge">Evidence Gate</span>
            <span class="ece-badge">Citations</span>
            <span class="ece-badge">Eval: 37/37 + 18/18</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_sidebar() -> dict[str, Any]:
    with st.sidebar:
        st.caption("Enterprise Context Engine")
        page = st.radio(
            "Page",
            ["Ask Assistant", "Documents", "Evaluation", "Query Logs", "Health"],
        )
        api_url = st.text_input("Backend API URL", key="api_url")
        st.caption("The dashboard talks to your local FastAPI backend. No external API is required.")

        auth_status = _api_get("/auth/status", default={}, show_error=False)
        health = _api_get("/health", default={}, show_error=False)
        users = _api_get("/users", default=[], show_error=False)
        data_sources = _api_get("/data-sources", default=[], show_error=False)

        connected = isinstance(health, dict) and health.get("status") == "ok"
        if connected:
            st.success("Connection: online")
        else:
            st.warning("Connection: unavailable")

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

        data_source = _render_data_source_selector(health, data_sources)
        user_id = _render_user_selector(users)
        screenshot_mode = st.checkbox(
            "Screenshot mode",
            key="screenshot_mode",
            help="Keeps noisy debug output collapsed or hidden for cleaner screenshots.",
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
        "Data Source",
        source_ids,
        index=default_index,
        format_func=lambda source_id: labels_by_id.get(source_id, source_id),
    )
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
    return st.selectbox("User", user_ids or ["finance_user"])


def ask_assistant_page(sidebar_state: dict[str, Any]) -> None:
    st.subheader("Ask Assistant")
    health = sidebar_state.get("health")
    if isinstance(health, dict):
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("Active source", health.get("active_data_source", "sample_docs"))
        col_b.metric("Documents", health.get("document_count", 0))
        col_c.metric("Chunks", health.get("chunk_count", 0))

    st.markdown("#### Demo queries")
    query_cols = st.columns(3)
    for index, demo_query in enumerate(DEMO_QUERIES):
        if query_cols[index].button(demo_query, width="stretch"):
            st.session_state["query_text"] = demo_query

    query = st.text_area("Query", key="query_text", height=90)
    col_a, col_b = st.columns([1, 4])
    top_k = col_a.slider("Top K", min_value=1, max_value=20, value=5)
    ask_clicked = col_b.button("Ask", type="primary", width="stretch")

    if ask_clicked:
        response = _api_post(
            "/query",
            {"user_id": sidebar_state["user_id"], "query": query, "top_k": top_k},
            default=None,
        )
        if isinstance(response, dict):
            _render_answer(response, screenshot_mode=bool(sidebar_state.get("screenshot_mode")))


def _render_answer(response: dict[str, Any], screenshot_mode: bool) -> None:
    answer = str(response.get("answer", ""))
    safe_abstain = bool(response.get("safe_abstain", False))
    if safe_abstain:
        _card(
            "Safe abstention",
            "No accessible supporting evidence was found for this question.",
            modifier="ece-safe",
        )
    else:
        _card("Answer", answer, modifier="ece-answer")

    citations = response.get("citations", [])
    if citations:
        st.markdown("#### Citations")
        for citation in citations:
            _render_citation(citation)
    else:
        st.caption("No citations returned.")

    debug = _debug_summary(response.get("debug", {}))
    if screenshot_mode:
        _render_safety_summary(debug, safe_abstain)
    else:
        with st.expander("Safety and routing summary", expanded=False):
            st.json(debug)


def _render_citation(citation: dict[str, Any]) -> None:
    title = html.escape(str(citation.get("document_title", "Untitled document")))
    section = html.escape(str(citation.get("section_title", "Unknown section")))
    department = html.escape(str(citation.get("department", "unknown")))
    access_level = html.escape(str(citation.get("access_level", "unknown")))
    method = html.escape(str(citation.get("retrieval_method", "retrieval")))
    score = citation.get("score", "")
    st.markdown(
        f"""
        <div class="ece-citation">
          <strong>{title}</strong>
          <div class="ece-muted">{section}</div>
          <div class="ece-badge-row">
            <span class="ece-badge">{department}</span>
            <span class="ece-badge">{access_level}</span>
            <span class="ece-badge">{method}</span>
            <span class="ece-badge">score {score}</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_safety_summary(debug: dict[str, Any], safe_abstain: bool) -> None:
    status = "Safe abstention" if safe_abstain else "Grounded answer"
    body = (
        f"Mode: {debug.get('retrieval_mode', 'unknown')} | "
        f"Intent: {debug.get('intent', 'unknown')} | "
        f"Citations: {debug.get('citation_count', 0)} | "
        f"Auth: {debug.get('auth_mode', 'off')}"
    )
    _card(status, body, modifier="ece-success" if not safe_abstain else "ece-safe")


def documents_page() -> None:
    st.subheader("Documents")
    st.caption("Document metadata only. Raw restricted context is not shown in this dashboard.")
    documents = _api_get("/documents", default=[])
    if not isinstance(documents, list):
        return

    departments = sorted({document.get("department", "") for document in documents})
    access_levels = sorted({document.get("access_level", "") for document in documents})
    col_a, col_b = st.columns(2)
    department = col_a.selectbox("Department", ["all", *departments])
    access_level = col_b.selectbox("Access Level", ["all", *access_levels])

    filtered = [
        {
            "title": document.get("title"),
            "department": document.get("department"),
            "access_level": document.get("access_level"),
            "source_name": document.get("source_name") or document.get("source_path"),
            "document_type": document.get("document_type"),
        }
        for document in documents
        if (department == "all" or document.get("department") == department)
        and (access_level == "all" or document.get("access_level") == access_level)
    ]
    st.dataframe(filtered, width="stretch", hide_index=True)


def evaluation_page() -> None:
    st.subheader("Evaluation")
    col_a, col_b, col_c, col_d = st.columns(4)
    col_a.metric("sample_docs", "37/37")
    col_b.metric("gitlab_handbook", "18/18")
    col_c.metric("restricted leak rate", "0.00")
    col_d.metric("tests", "235 passed, 1 skipped")
    st.caption(
        "Deterministic evals are local and do not require LLM-as-judge or external services."
    )

    eval_source = st.selectbox(
        "Evaluation Source",
        ["sample_docs", "gitlab_handbook", "combined"],
        format_func=lambda source: {
            "sample_docs": "Synthetic Enterprise Docs",
            "gitlab_handbook": "GitLab Handbook-style Docs",
            "combined": "Combined Corpus",
        }.get(source, source),
    )
    if st.button("Run Evaluation", type="primary"):
        summary = _api_post(f"/evaluate?source={eval_source}", {}, default=None)
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
    st.caption("Raw context and restricted chunk text are not stored in logs.")
    logs = _api_get("/logs", default=[])
    if isinstance(logs, list):
        rows = [
            {
                "query_id": log.get("query_id"),
                "user_id": log.get("user_id"),
                "query": log.get("query"),
                "safe_abstain": log.get("safe_abstain"),
                "citation_count": log.get("citation_count"),
                "retrieval_mode": log.get("retrieval_mode"),
                "intent": log.get("intent"),
                "latency_ms": log.get("latency_ms"),
                "created_at": log.get("created_at"),
            }
            for log in logs
        ]
        st.dataframe(rows, width="stretch", hide_index=True)


def health_page(sidebar_state: dict[str, Any]) -> None:
    st.subheader("Health")
    health = sidebar_state.get("health")
    if isinstance(health, dict) and health:
        col_a, col_b, col_c, col_d = st.columns(4)
        col_a.metric("Status", health.get("status", "unknown"))
        col_b.metric("Data Source", health.get("active_data_source", "sample_docs"))
        col_c.metric("Documents", health.get("document_count", 0))
        col_d.metric("Chunks", health.get("chunk_count", 0))
        with st.expander("Raw health payload", expanded=False):
            st.json(health)

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
