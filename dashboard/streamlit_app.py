"""Streamlit dashboard for the Enterprise Context Engine API."""

from __future__ import annotations

import os
from typing import Any

import requests
import streamlit as st

API_URL = os.getenv("ECE_API_URL", "http://localhost:8000").rstrip("/")


def main() -> None:
    st.set_page_config(page_title="Enterprise Context Engine", layout="wide")
    st.title("Enterprise Context Engine")

    page = st.sidebar.radio(
        "Page",
        ["Ask Assistant", "Documents", "Evaluation", "Query Logs", "Health"],
    )
    st.sidebar.caption(API_URL)
    auth_status = _api_get("/auth/status", default={})
    if isinstance(auth_status, dict):
        st.sidebar.caption(f"Auth: {auth_status.get('auth_mode', 'off')}")
    st.sidebar.text_input("API key", type="password", key="api_key")

    if page == "Ask Assistant":
        ask_assistant_page()
    elif page == "Documents":
        documents_page()
    elif page == "Evaluation":
        evaluation_page()
    elif page == "Query Logs":
        query_logs_page()
    else:
        health_page()


def ask_assistant_page() -> None:
    st.header("Ask Assistant")
    health = _api_get("/health", default={})
    if isinstance(health, dict):
        st.info(f"Active data source: {health.get('active_data_source', 'sample_docs')}")
    users = _api_get("/users", default=[])
    user_ids = [user["user_id"] for user in users] if isinstance(users, list) else []
    user_id = st.selectbox("User", user_ids or ["finance_user"])
    query = st.text_input("Query", value="What is the invoice approval limit?")
    top_k = st.slider("Top K", min_value=1, max_value=20, value=5)

    if st.button("Ask", type="primary"):
        response = _api_post(
            "/query",
            {"user_id": user_id, "query": query, "top_k": top_k},
            default=None,
        )
        if not isinstance(response, dict):
            return
        st.subheader("Answer")
        st.write(response.get("answer", ""))
        st.metric("Safe Abstain", str(response.get("safe_abstain", False)))
        citations = response.get("citations", [])
        if citations:
            st.subheader("Citations")
            st.dataframe(citations, use_container_width=True)
        st.subheader("Debug")
        debug = response.get("debug", {})
        st.json(_debug_summary(debug))


def documents_page() -> None:
    st.header("Documents")
    documents = _api_get("/documents", default=[])
    if not isinstance(documents, list):
        return

    departments = sorted({document.get("department", "") for document in documents})
    access_levels = sorted({document.get("access_level", "") for document in documents})
    col_a, col_b = st.columns(2)
    department = col_a.selectbox("Department", ["all", *departments])
    access_level = col_b.selectbox("Access Level", ["all", *access_levels])

    filtered = [
        document
        for document in documents
        if (department == "all" or document.get("department") == department)
        and (access_level == "all" or document.get("access_level") == access_level)
    ]
    st.dataframe(filtered, use_container_width=True)


def evaluation_page() -> None:
    st.header("Evaluation")
    st.info(
        "sample_docs eval tests enterprise access-control behavior. "
        "gitlab_handbook eval tests public handbook-style real-source retrieval. "
        "combined eval runs both sets together and is experimental."
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
    st.header("Query Logs")
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
        st.dataframe(rows, use_container_width=True)


def health_page() -> None:
    st.header("Health")
    health = _api_get("/health", default={})
    if isinstance(health, dict):
        col_a, col_b, col_c, col_d = st.columns(4)
        col_a.metric("Status", health.get("status", "unknown"))
        col_b.metric("Data Source", health.get("active_data_source", "sample_docs"))
        col_c.metric("Documents", health.get("document_count", 0))
        col_d.metric("Chunks", health.get("chunk_count", 0))
        st.json(health)

    st.subheader("Data Source")
    data_sources = _api_get("/data-sources", default=[])
    if isinstance(data_sources, list) and data_sources:
        labels_by_id = {item["id"]: item["label"] for item in data_sources}
        descriptions_by_id = {item["id"]: item.get("description", "") for item in data_sources}
        source_ids = list(labels_by_id)
        current_source = health.get("active_data_source", "sample_docs") if isinstance(health, dict) else "sample_docs"
        default_index = source_ids.index(current_source) if current_source in source_ids else 0
        selected_source = st.selectbox(
            "Corpus",
            source_ids,
            index=default_index,
            format_func=lambda source_id: labels_by_id.get(source_id, source_id),
        )
        st.caption(descriptions_by_id.get(selected_source, ""))
        if st.button("Load Data Source", type="primary"):
            result = _api_post("/ingest/data-source", {"mode": selected_source}, default=None)
            if isinstance(result, dict):
                st.success(
                    f"Loaded {result.get('active_data_source')} with "
                    f"{result.get('documents_ingested', 0)} documents and "
                    f"{result.get('chunks_created', 0)} chunks."
                )

    if st.button("Ingest Sample Docs"):
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
            use_container_width=True,
        )


def _api_get(path: str, default: Any) -> Any:
    try:
        response = requests.get(f"{API_URL}{path}", headers=_api_headers(), timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        st.error(f"API request failed: {exc}")
        return default


def _api_post(path: str, payload: dict[str, Any], default: Any) -> Any:
    try:
        response = requests.post(f"{API_URL}{path}", json=payload, headers=_api_headers(), timeout=120)
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
    api_key = str(st.session_state.get("api_key", "") or "").strip()
    if not api_key:
        return {}
    return {"X-API-Key": api_key}


if __name__ == "__main__":
    main()
