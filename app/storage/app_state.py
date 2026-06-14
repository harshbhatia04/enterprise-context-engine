"""Process-local application state for the FastAPI MVP."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Any

from app.config import PROJECT_ROOT, SAMPLE_DOCS_DIR
from app.evaluation.sample_eval_set import get_sample_eval_set
from app.ingestion.pipeline import ingest_directory
from app.ingestion.real_data.gitlab_handbook import ingest_gitlab_handbook_directory
from app.schemas import Chunk, Document, EvalSummary
from app.storage.query_log_store import InMemoryQueryLogStore, QueryLogEntry, sanitize_query_debug
from app.storage.sqlite_store import SQLiteStore
from scripts.create_sample_docs import create_sample_docs

GITLAB_HANDBOOK_DIR = PROJECT_ROOT / "data" / "real_sources" / "gitlab_handbook"
SAMPLE_DOCS = "sample_docs"
GITLAB_HANDBOOK = "gitlab_handbook"
COMBINED = "combined"
ALLOWED_DATA_SOURCES = {SAMPLE_DOCS, GITLAB_HANDBOOK, COMBINED}
MEMORY_BACKEND = "memory"
SQLITE_BACKEND = "sqlite"
DEFAULT_SQLITE_PATH = "data/state/enterprise_context_engine.db"


@dataclass
class AppState:
    active_data_source: str = SAMPLE_DOCS
    documents: list[Document] = field(default_factory=list)
    chunks: list[Chunk] = field(default_factory=list)
    query_logs: InMemoryQueryLogStore = field(default_factory=InMemoryQueryLogStore)
    last_eval_summary: EvalSummary | None = None
    last_eval_source: str | None = None
    is_ingested: bool = False


_APP_STATE = AppState()
_SQLITE_STORE: SQLiteStore | None = None
_SQLITE_STORE_PATH: str | None = None


def get_app_state() -> AppState:
    """Return the process-local app state singleton."""
    return _APP_STATE


def reset_app_state() -> None:
    """Reset app state for tests and local demos."""
    global _APP_STATE, _SQLITE_STORE, _SQLITE_STORE_PATH
    _APP_STATE = AppState()
    _SQLITE_STORE = None
    _SQLITE_STORE_PATH = None


def get_storage_backend() -> str:
    """Return active storage backend: memory or sqlite."""
    backend = os.getenv("ECE_STORAGE_BACKEND", MEMORY_BACKEND).strip().lower()
    if backend not in {MEMORY_BACKEND, SQLITE_BACKEND}:
        return MEMORY_BACKEND
    return backend


def get_sqlite_path() -> str:
    """Return configured SQLite path without forcing SQLite mode."""
    return os.getenv("ECE_SQLITE_PATH", DEFAULT_SQLITE_PATH)


def is_sqlite_enabled() -> bool:
    """Return whether optional SQLite persistence is enabled."""
    return get_storage_backend() == SQLITE_BACKEND


def get_sqlite_store() -> SQLiteStore:
    """Return a cached SQLite store for the configured path."""
    global _SQLITE_STORE, _SQLITE_STORE_PATH
    resolved_path = _resolve_sqlite_path(get_sqlite_path())
    if _SQLITE_STORE is None or _SQLITE_STORE_PATH != resolved_path:
        _SQLITE_STORE = SQLiteStore(resolved_path)
        _SQLITE_STORE.initialize()
        _SQLITE_STORE_PATH = resolved_path
    return _SQLITE_STORE


def load_sample_docs() -> tuple[list[Document], list[Chunk]]:
    """Load deterministic synthetic enterprise sample docs."""
    if not sorted(SAMPLE_DOCS_DIR.glob("*.md")):
        create_sample_docs(SAMPLE_DOCS_DIR)
    return ingest_directory(SAMPLE_DOCS_DIR)


def load_gitlab_handbook_docs() -> tuple[list[Document], list[Chunk]]:
    """Load local GitLab Handbook-style public docs."""
    markdown_files = [
        path
        for path in sorted(GITLAB_HANDBOOK_DIR.glob("*.md"))
        if path.name.lower() != "readme.md"
    ]
    if not markdown_files:
        raise FileNotFoundError(
            "No GitLab Handbook-style Markdown files found. "
            "Run: python scripts/create_gitlab_fixture_docs.py"
        )
    return ingest_gitlab_handbook_directory(GITLAB_HANDBOOK_DIR)


def load_data_source(mode: str) -> AppState:
    """Load one supported data source mode into process memory."""
    normalized_mode = str(mode or SAMPLE_DOCS).strip().lower()
    if normalized_mode not in ALLOWED_DATA_SOURCES:
        raise ValueError(
            f"Unsupported data source mode: {mode}. "
            f"Allowed modes: {', '.join(sorted(ALLOWED_DATA_SOURCES))}"
        )

    state = get_app_state()
    if state.is_ingested and state.active_data_source == normalized_mode:
        return state

    if normalized_mode == SAMPLE_DOCS:
        documents, chunks = load_sample_docs()
    elif normalized_mode == GITLAB_HANDBOOK:
        documents, chunks = load_gitlab_handbook_docs()
    else:
        sample_documents, sample_chunks = load_sample_docs()
        gitlab_documents, gitlab_chunks = load_gitlab_handbook_docs()
        documents = [*sample_documents, *gitlab_documents]
        chunks = [*sample_chunks, *gitlab_chunks]

    if state.active_data_source != normalized_mode or state.is_ingested:
        state.query_logs.clear()
        if is_sqlite_enabled():
            get_sqlite_store().clear_query_logs()
    state.documents = documents
    state.chunks = chunks
    state.active_data_source = normalized_mode
    state.is_ingested = True
    if is_sqlite_enabled():
        store = get_sqlite_store()
        store.clear_documents_and_chunks()
        store.save_documents(documents)
        store.save_chunks(chunks)
    return state


def get_available_data_sources() -> list[dict]:
    """Return selectable data-source metadata for API and dashboard."""
    return [
        {
            "id": SAMPLE_DOCS,
            "label": "Synthetic Enterprise Docs",
            "description": "Deterministic sample policies used for tests and demos.",
        },
        {
            "id": GITLAB_HANDBOOK,
            "label": "GitLab Handbook-style Docs",
            "description": "Local public handbook-style fixture docs for real-data ingestion demo.",
        },
        {
            "id": COMBINED,
            "label": "Combined Corpus",
            "description": "Synthetic enterprise docs plus GitLab Handbook-style docs.",
        },
    ]


def ensure_active_data_source_loaded() -> AppState:
    """Load the default sample corpus if no data source is active in memory."""
    state = get_app_state()
    if state.is_ingested:
        return state
    return load_data_source(SAMPLE_DOCS)


def ensure_sample_docs_ingested() -> AppState:
    """Create sample docs when needed and load them into memory once."""
    return load_data_source(SAMPLE_DOCS)


def sample_eval_count() -> int:
    """Return the number of bundled sample eval examples."""
    return len(get_sample_eval_set())


def create_query_log(
    user_id: str,
    query: str,
    answer: str,
    safe_abstain: bool,
    citation_count: int,
    retrieval_mode: str | None,
    intent: str | None,
    latency_ms: float | None,
    debug: dict[str, Any] | None = None,
) -> QueryLogEntry:
    """Create a sanitized query log in memory and optional SQLite."""
    state = get_app_state()
    if is_sqlite_enabled():
        entry = QueryLogEntry(
            query_id=get_sqlite_store().next_query_id(),
            user_id=user_id,
            query=query,
            answer=answer,
            safe_abstain=safe_abstain,
            citation_count=citation_count,
            retrieval_mode=retrieval_mode,
            intent=intent,
            latency_ms=latency_ms,
            created_at=datetime.now(timezone.utc).isoformat(),
            debug=sanitize_query_debug(debug or {}),
        )
        state.query_logs.add(entry)
        get_sqlite_store().add_query_log(entry)
        return entry

    return state.query_logs.create_entry(
        user_id=user_id,
        query=query,
        answer=answer,
        safe_abstain=safe_abstain,
        citation_count=citation_count,
        retrieval_mode=retrieval_mode,
        intent=intent,
        latency_ms=latency_ms,
        debug=debug,
    )


def list_query_logs(limit: int = 50) -> list[QueryLogEntry]:
    """List query logs from the active backend."""
    if is_sqlite_enabled():
        return get_sqlite_store().list_query_logs(limit=limit)
    return get_app_state().query_logs.list(limit=limit)


def save_eval_summary(source: str, summary: EvalSummary) -> None:
    """Save latest eval summary in memory and optional SQLite."""
    state = get_app_state()
    state.last_eval_summary = summary
    state.last_eval_source = source
    if is_sqlite_enabled():
        get_sqlite_store().save_eval_summary(source, summary)


def load_latest_eval_summary() -> dict | None:
    """Load latest eval summary payload from SQLite when enabled."""
    if not is_sqlite_enabled():
        return None
    return get_sqlite_store().load_latest_eval_summary()


def _resolve_sqlite_path(path_text: str) -> str:
    path = Path(path_text)
    if path.is_absolute():
        return str(path)
    return str(PROJECT_ROOT / path)
