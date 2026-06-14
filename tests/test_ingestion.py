from pathlib import Path

from app.ingestion.loaders import load_markdown_directory, load_markdown_file
from app.ingestion.metadata import parse_frontmatter
from app.ingestion.pipeline import ingest_directory
from scripts.create_sample_docs import create_sample_docs


REQUIRED_KEYS = {
    "title",
    "department",
    "access_level",
    "version",
    "effective_date",
    "document_type",
}


def test_frontmatter_parsing_works() -> None:
    markdown = """---
title: "Engineering Rollback Procedure"
department: "engineering"
access_level: "engineering"
version: "1.0"
effective_date: "2026-01-01"
document_type: "procedure"
---

# Engineering Rollback Procedure

Body text.
"""

    metadata, body = parse_frontmatter(markdown)

    assert metadata["title"] == "Engineering Rollback Procedure"
    assert metadata["department"] == "engineering"
    assert metadata["document_type"] == "procedure"
    assert body.startswith("# Engineering Rollback Procedure")
    assert "---" not in body


def test_missing_frontmatter_does_not_crash() -> None:
    metadata, body = parse_frontmatter("# Plain Document\n\nNo metadata here.")

    assert metadata == {}
    assert body == "# Plain Document\n\nNo metadata here."


def test_markdown_file_loader_applies_defaults(tmp_path: Path) -> None:
    path = tmp_path / "plain-doc.md"
    path.write_text("# Plain Doc\n\nBody.", encoding="utf-8")

    document = load_markdown_file(path)

    assert document.document_id == "plain-doc"
    assert document.title == "Plain Doc"
    assert document.department == "general"
    assert document.access_level == "general"
    assert document.version == "unknown"
    assert document.effective_date == "unknown"
    assert document.body == "# Plain Doc\n\nBody."


def test_markdown_directory_loader_loads_24_generated_docs(tmp_path: Path) -> None:
    create_sample_docs(tmp_path)

    documents = load_markdown_directory(tmp_path)

    assert len(documents) == 24
    assert documents == sorted(documents, key=lambda document: document.source_path)


def test_documents_contain_required_metadata(tmp_path: Path) -> None:
    create_sample_docs(tmp_path)
    documents = load_markdown_directory(tmp_path)

    for document in documents:
        assert REQUIRED_KEYS.issubset(document.metadata)
        assert document.department in {"hr", "finance", "engineering", "legal"}
        assert document.access_level == document.department
        assert document.version == "1.0"
        assert document.effective_date == "2026-01-01"
        assert document.body


def test_ingestion_pipeline_returns_documents_and_chunks(tmp_path: Path) -> None:
    create_sample_docs(tmp_path)

    documents, chunks = ingest_directory(tmp_path)

    assert len(documents) == 24
    assert chunks
    assert {chunk.document_id for chunk in chunks}.issubset(
        {document.document_id for document in documents}
    )
