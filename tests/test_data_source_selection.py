import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.storage.app_state import reset_app_state
from scripts.create_gitlab_fixture_docs import create_gitlab_fixture_docs


@pytest.fixture(autouse=True)
def reset_state() -> None:
    reset_app_state()


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def test_available_data_sources(client: TestClient) -> None:
    response = client.get("/data-sources")
    source_ids = {source["id"] for source in response.json()}

    assert response.status_code == 200
    assert source_ids == {"sample_docs", "gitlab_handbook", "combined"}


def test_load_sample_docs_data_source(client: TestClient) -> None:
    response = client.post("/ingest/data-source", json={"mode": "sample_docs"})
    payload = response.json()

    assert response.status_code == 200
    assert payload["active_data_source"] == "sample_docs"
    assert payload["documents_ingested"] == 24
    assert payload["chunks_created"] == 120


def test_load_gitlab_handbook_data_source(client: TestClient) -> None:
    create_gitlab_fixture_docs()

    response = client.post("/ingest/data-source", json={"mode": "gitlab_handbook"})
    payload = response.json()

    assert response.status_code == 200
    assert payload["active_data_source"] == "gitlab_handbook"
    assert payload["documents_ingested"] >= 8
    assert payload["chunks_created"] >= 8


def test_load_combined_returns_more_documents_than_sample_docs(client: TestClient) -> None:
    create_gitlab_fixture_docs()
    sample = client.post("/ingest/data-source", json={"mode": "sample_docs"}).json()

    combined = client.post("/ingest/data-source", json={"mode": "combined"}).json()

    assert combined["active_data_source"] == "combined"
    assert combined["documents_ingested"] > sample["documents_ingested"]


def test_health_includes_active_data_source(client: TestClient) -> None:
    create_gitlab_fixture_docs()
    client.post("/ingest/data-source", json={"mode": "gitlab_handbook"})

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["active_data_source"] == "gitlab_handbook"


def test_documents_include_source_metadata_for_gitlab_docs(client: TestClient) -> None:
    create_gitlab_fixture_docs()
    client.post("/ingest/data-source", json={"mode": "gitlab_handbook"})

    response = client.get("/documents")
    documents = response.json()

    assert response.status_code == 200
    assert documents
    assert all(document["source_name"] == "gitlab_handbook" for document in documents)
    assert all(document["source_url"] == "https://handbook.gitlab.com/" for document in documents)


def test_query_uses_active_gitlab_public_corpus_for_intern(client: TestClient) -> None:
    create_gitlab_fixture_docs()
    client.post("/ingest/data-source", json={"mode": "gitlab_handbook"})

    response = client.post(
        "/query",
        json={
            "user_id": "intern_user",
            "query": "What does the handbook say about remote work?",
            "top_k": 5,
        },
    )
    payload = response.json()

    assert response.status_code == 200
    assert payload["safe_abstain"] is False
    assert payload["citations"]
    assert payload["debug"]["active_data_source"] == "gitlab_handbook"
    assert any(citation["access_level"] == "public" for citation in payload["citations"])


def test_logs_clear_when_data_source_changes(client: TestClient) -> None:
    create_gitlab_fixture_docs()
    client.post("/ingest/data-source", json={"mode": "sample_docs"})
    client.post(
        "/query",
        json={
            "user_id": "finance_user",
            "query": "What is the invoice approval limit?",
            "top_k": 5,
        },
    )
    assert client.get("/logs").json()

    client.post("/ingest/data-source", json={"mode": "gitlab_handbook"})

    assert client.get("/logs").json() == []


def test_invalid_data_source_mode_returns_error(client: TestClient) -> None:
    response = client.post("/ingest/data-source", json={"mode": "unknown"})

    assert response.status_code == 400
    assert "Unsupported data source mode" in response.json()["detail"]


def test_existing_sample_doc_query_still_works(client: TestClient) -> None:
    client.post("/ingest/data-source", json={"mode": "sample_docs"})

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
    assert payload["citations"]
    assert payload["debug"]["active_data_source"] == "sample_docs"
