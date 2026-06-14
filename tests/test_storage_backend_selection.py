from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.storage.app_state import (
    SAMPLE_DOCS,
    get_sqlite_path,
    get_sqlite_store,
    get_storage_backend,
    is_sqlite_enabled,
    load_data_source,
    reset_app_state,
)
from app.storage.sqlite_store import SQLiteStore


def enable_sqlite(monkeypatch, tmp_path: Path) -> Path:
    db_path = tmp_path / "state.db"
    monkeypatch.setenv("ECE_STORAGE_BACKEND", "sqlite")
    monkeypatch.setenv("ECE_SQLITE_PATH", str(db_path))
    reset_app_state()
    return db_path


def test_default_backend_is_memory(monkeypatch) -> None:
    monkeypatch.delenv("ECE_STORAGE_BACKEND", raising=False)
    reset_app_state()

    assert get_storage_backend() == "memory"
    assert is_sqlite_enabled() is False


def test_env_var_selects_sqlite(monkeypatch, tmp_path: Path) -> None:
    enable_sqlite(monkeypatch, tmp_path)

    assert get_storage_backend() == "sqlite"
    assert is_sqlite_enabled() is True


def test_sqlite_path_env_var_is_respected(monkeypatch, tmp_path: Path) -> None:
    db_path = enable_sqlite(monkeypatch, tmp_path)

    assert get_sqlite_path() == str(db_path)
    assert get_sqlite_store().db_path == str(db_path)


def test_app_state_loads_sample_docs_with_sqlite_backend(monkeypatch, tmp_path: Path) -> None:
    db_path = enable_sqlite(monkeypatch, tmp_path)

    state = load_data_source(SAMPLE_DOCS)
    reopened = SQLiteStore(str(db_path))

    assert state.documents
    assert state.chunks
    assert len(reopened.load_documents()) == len(state.documents)
    assert len(reopened.load_chunks()) == len(state.chunks)


def test_api_health_reports_storage_backend(monkeypatch, tmp_path: Path) -> None:
    db_path = enable_sqlite(monkeypatch, tmp_path)
    client = TestClient(app)

    payload = client.get("/health").json()

    assert payload["storage_backend"] == "sqlite"
    assert payload["sqlite_path"] == str(db_path)


def test_api_logs_work_under_sqlite_backend(monkeypatch, tmp_path: Path) -> None:
    enable_sqlite(monkeypatch, tmp_path)
    client = TestClient(app)

    response = client.post(
        "/query",
        json={"user_id": "finance_user", "query": "What is the invoice approval limit?", "top_k": 5},
    )
    logs = client.get("/logs").json()

    assert response.status_code == 200
    assert logs
    assert logs[0]["query_id"] == "query_000001"
    assert "context_text" not in str(logs[0])


def test_api_evaluate_saves_metrics_under_sqlite_backend(monkeypatch, tmp_path: Path) -> None:
    db_path = enable_sqlite(monkeypatch, tmp_path)
    client = TestClient(app)

    response = client.post("/evaluate?source=sample_docs")
    reopened = SQLiteStore(str(db_path))
    latest = reopened.load_latest_eval_summary()

    assert response.status_code == 200
    assert latest is not None
    assert latest["source"] == "sample_docs"
    assert latest["metrics"]["pass_rate"] == 1.0
