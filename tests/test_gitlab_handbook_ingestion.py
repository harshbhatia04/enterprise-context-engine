from pathlib import Path

from app.ingestion.pipeline import ingest_directory
from app.ingestion.real_data.gitlab_handbook import (
    infer_gitlab_department,
    ingest_gitlab_handbook_directory,
    load_gitlab_handbook_directory,
)
from app.schemas import Document
from scripts.create_gitlab_fixture_docs import create_gitlab_fixture_docs
from scripts.create_sample_docs import create_sample_docs


def test_infer_gitlab_department_maps_remote_work_and_onboarding_to_hr() -> None:
    assert infer_gitlab_department("people/remote-work.md", "Remote Work", "") == "hr"
    assert infer_gitlab_department("team/onboarding.md", "Team Member Onboarding", "") == "hr"


def test_infer_gitlab_department_maps_incident_and_engineering_to_engineering() -> None:
    assert infer_gitlab_department("engineering/incident.md", "Incident Management", "") == "engineering"
    assert infer_gitlab_department("development/process.md", "Engineering Development", "") == "engineering"


def test_infer_gitlab_department_maps_expense_and_finance_to_finance() -> None:
    assert infer_gitlab_department("finance/expense.md", "Travel Expenses", "") == "finance"
    assert infer_gitlab_department("accounting/procurement.md", "Procurement", "") == "finance"


def test_infer_gitlab_department_maps_privacy_and_compliance_to_legal() -> None:
    assert infer_gitlab_department("legal/privacy.md", "Privacy Compliance", "") == "legal"
    assert infer_gitlab_department("contracts/compliance.md", "Contract Compliance", "") == "legal"


def test_fixture_script_creates_at_least_8_markdown_files(tmp_path: Path) -> None:
    created = create_gitlab_fixture_docs(tmp_path)

    assert len(created) >= 8
    assert len(list(tmp_path.glob("*.md"))) >= 8


def test_loader_loads_fixture_docs_as_documents(tmp_path: Path) -> None:
    create_gitlab_fixture_docs(tmp_path)

    documents = load_gitlab_handbook_directory(tmp_path)

    assert documents
    assert all(isinstance(document, Document) for document in documents)
    assert all(document.document_id.startswith("gitlab-") for document in documents)


def test_ingestion_returns_documents_and_chunks(tmp_path: Path) -> None:
    create_gitlab_fixture_docs(tmp_path)

    documents, chunks = ingest_gitlab_handbook_directory(tmp_path)

    assert len(documents) >= 8
    assert chunks
    assert {chunk.document_id for chunk in chunks}.issubset({doc.document_id for doc in documents})


def test_gitlab_fixture_docs_have_public_source_metadata(tmp_path: Path) -> None:
    create_gitlab_fixture_docs(tmp_path)

    documents = load_gitlab_handbook_directory(tmp_path)

    assert all(document.metadata["source_name"] == "gitlab_handbook" for document in documents)
    assert all(document.access_level == "public" for document in documents)
    assert all(document.document_type == "handbook" for document in documents)
    assert all(document.metadata["source_url"] == "https://handbook.gitlab.com/" for document in documents)


def test_chunks_preserve_source_metadata(tmp_path: Path) -> None:
    create_gitlab_fixture_docs(tmp_path)

    _, chunks = ingest_gitlab_handbook_directory(tmp_path)

    assert chunks
    assert all(chunk.access_level == "public" for chunk in chunks)
    assert all(chunk.document_type == "handbook" for chunk in chunks)
    assert all(str(tmp_path) in chunk.source_path for chunk in chunks)


def test_existing_sample_doc_ingestion_still_works(tmp_path: Path) -> None:
    create_sample_docs(tmp_path)

    documents, chunks = ingest_directory(tmp_path)

    assert len(documents) == 24
    assert len(chunks) == 120
