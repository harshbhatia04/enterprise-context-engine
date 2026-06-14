import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.storage.app_state import reset_app_state


@pytest.fixture(autouse=True)
def reset_state() -> None:
    reset_app_state()


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def test_root_returns_ok(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"name": "Enterprise Context Engine", "status": "ok"}


def test_ingest_sample_returns_document_and_chunk_counts(client: TestClient) -> None:
    response = client.post("/ingest/sample")
    payload = response.json()

    assert response.status_code == 200
    assert payload["status"] == "ok"
    assert payload["documents_ingested"] == 24
    assert payload["chunks_created"] == 120

    second = client.post("/ingest/sample").json()
    assert second["documents_ingested"] == 24
    assert second["chunks_created"] == 120


def test_health_returns_counts_after_ingest(client: TestClient) -> None:
    client.post("/ingest/sample")

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["is_ingested"] is True
    assert response.json()["document_count"] == 24
    assert response.json()["chunk_count"] == 120


def test_users_includes_demo_users(client: TestClient) -> None:
    response = client.get("/users")
    user_ids = {user["user_id"] for user in response.json()}

    assert {"finance_user", "intern_user", "admin_user"}.issubset(user_ids)


def test_documents_return_metadata_without_body(client: TestClient) -> None:
    response = client.get("/documents")
    documents = response.json()

    assert response.status_code == 200
    assert documents
    assert "body" not in documents[0]
    assert {"document_id", "title", "department", "access_level", "source_path"}.issubset(documents[0])


def test_query_finance_user_returns_answer_with_citations(client: TestClient) -> None:
    response = client.post(
        "/query",
        json={
            "user_id": "finance_user",
            "query": "What is the invoice approval limit?",
            "top_k": 5,
        },
    )
    payload = response.json()

    assert response.status_code == 200
    assert payload["safe_abstain"] is False
    assert payload["answer"]
    assert payload["citations"]
    assert payload["debug"]["retrieval_mode"] == "hybrid"
    assert payload["debug"]["auth_mode"] == "off"


def test_auth_status_returns_off_by_default(client: TestClient) -> None:
    response = client.get("/auth/status")

    assert response.status_code == 200
    assert response.json() == {"auth_mode": "off", "enabled": False}


def test_query_intern_finance_safe_abstains_without_title_leak(client: TestClient) -> None:
    response = client.post(
        "/query",
        json={
            "user_id": "intern_user",
            "query": "What is the invoice approval limit?",
            "top_k": 5,
        },
    )
    payload = response.json()

    assert response.status_code == 200
    assert payload["safe_abstain"] is True
    assert payload["citations"] == []
    assert "Invoice Approval Policy" not in str(payload)


def test_logs_return_query_logs_after_query(client: TestClient) -> None:
    client.post(
        "/query",
        json={
            "user_id": "finance_user",
            "query": "What is the invoice approval limit?",
            "top_k": 5,
        },
    )

    response = client.get("/logs")
    logs = response.json()

    assert response.status_code == 200
    assert logs
    assert logs[0]["query_id"] == "query_000001"
    assert logs[0]["retrieval_mode"] == "hybrid"
    assert "context_text" not in str(logs[0])
    assert "focused_chunks" not in str(logs[0])


def test_evaluate_returns_metrics_with_pass_rate(client: TestClient) -> None:
    response = client.post("/evaluate")
    payload = response.json()

    assert response.status_code == 200
    assert payload["total_examples"] >= 30
    assert "pass_rate" in payload["metrics"]


def test_metrics_returns_latest_metrics_after_evaluation(client: TestClient) -> None:
    before = client.get("/metrics").json()
    assert before == {"status": "no_evaluation_run"}

    client.post("/evaluate")
    response = client.get("/metrics")
    payload = response.json()

    assert response.status_code == 200
    assert "pass_rate" in payload["metrics"]
    assert payload["failed_examples"] == 0


def test_api_key_auth_query_without_key_returns_401(monkeypatch, client: TestClient) -> None:
    monkeypatch.setenv("ECE_AUTH_MODE", "api_key")

    response = client.post(
        "/query",
        json={
            "user_id": "finance_user",
            "query": "What is the invoice approval limit?",
            "top_k": 5,
        },
    )

    assert response.status_code == 401


def test_api_key_auth_query_with_wrong_key_returns_401(monkeypatch, client: TestClient) -> None:
    monkeypatch.setenv("ECE_AUTH_MODE", "api_key")

    response = client.post(
        "/query",
        headers={"X-API-Key": "wrong-key"},
        json={
            "user_id": "finance_user",
            "query": "What is the invoice approval limit?",
            "top_k": 5,
        },
    )

    assert response.status_code == 401


def test_api_key_auth_finance_key_with_finance_user_succeeds(monkeypatch, client: TestClient) -> None:
    monkeypatch.setenv("ECE_AUTH_MODE", "api_key")

    response = client.post(
        "/query",
        headers={"X-API-Key": "dev-finance-key"},
        json={
            "user_id": "finance_user",
            "query": "What is the invoice approval limit?",
            "top_k": 5,
        },
    )
    payload = response.json()

    assert response.status_code == 200
    assert payload["user_id"] == "finance_user"
    assert payload["safe_abstain"] is False
    assert payload["debug"]["auth_mode"] == "api_key"
    assert payload["debug"]["authenticated_user_id"] == "finance_user"
    assert "dev-finance-key" not in str(payload)


def test_api_key_auth_rejects_user_id_spoofing(monkeypatch, client: TestClient) -> None:
    monkeypatch.setenv("ECE_AUTH_MODE", "api_key")

    response = client.post(
        "/query",
        headers={"X-API-Key": "dev-finance-key"},
        json={
            "user_id": "intern_user",
            "query": "What is the invoice approval limit?",
            "top_k": 5,
        },
    )

    assert response.status_code == 403


def test_api_key_auth_intern_key_uses_intern_permissions(monkeypatch, client: TestClient) -> None:
    monkeypatch.setenv("ECE_AUTH_MODE", "api_key")

    response = client.post(
        "/query",
        headers={"Authorization": "Bearer dev-intern-key"},
        json={
            "user_id": "intern_user",
            "query": "What is the invoice approval limit?",
            "top_k": 5,
        },
    )
    payload = response.json()

    assert response.status_code == 200
    assert payload["user_id"] == "intern_user"
    assert payload["safe_abstain"] is True
    assert payload["citations"] == []
    assert payload["debug"]["authenticated_user_id"] == "intern_user"
    assert "dev-intern-key" not in str(payload)
