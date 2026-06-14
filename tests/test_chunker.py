from app.ingestion.chunker import chunk_document
from app.schemas import Document


def make_document(body: str) -> Document:
    return Document(
        document_id="engineering-rollback-procedure",
        title="Engineering Rollback Procedure",
        department="engineering",
        access_level="engineering",
        version="1.0",
        effective_date="2026-01-01",
        document_type="procedure",
        source_path="memory.md",
        body=body,
        metadata={
            "title": "Engineering Rollback Procedure",
            "department": "engineering",
            "access_level": "engineering",
            "version": "1.0",
            "effective_date": "2026-01-01",
            "document_type": "procedure",
        },
    )


def test_chunker_preserves_document_metadata() -> None:
    chunks = chunk_document(make_document("# Title\n\n## Emergency Rollback Steps\n\nDo the rollback."))

    assert chunks
    assert chunks[0].document_title == "Engineering Rollback Procedure"
    assert chunks[0].department == "engineering"
    assert chunks[0].access_level == "engineering"
    assert chunks[0].version == "1.0"


def test_chunker_preserves_section_titles() -> None:
    document = make_document(
        "# Engineering Rollback Procedure\n\n"
        "Intro.\n\n"
        "## Emergency Rollback Steps\n\n"
        "Restore the previous release.\n\n"
        "### Verification\n\n"
        "Check service health."
    )

    chunks = chunk_document(document)

    assert [chunk.section_title for chunk in chunks] == [
        "Engineering Rollback Procedure",
        "Emergency Rollback Steps",
        "Verification",
    ]


def test_chunk_ids_are_deterministic() -> None:
    document = make_document("# Title\n\n## One\n\nAlpha.\n\n## Two\n\nBeta.")

    first_run = [chunk.chunk_id for chunk in chunk_document(document)]
    second_run = [chunk.chunk_id for chunk in chunk_document(document)]

    assert first_run == second_run
    assert first_run == [
        "engineering-rollback-procedure::chunk_0000",
        "engineering-rollback-procedure::chunk_0001",
    ]


def test_long_sections_are_split_into_multiple_chunks() -> None:
    long_text = " ".join(f"word{i}" for i in range(95))
    document = make_document(f"## Large Section\n\n{long_text}")

    chunks = chunk_document(document, target_words=30, overlap_words=10)

    assert len(chunks) > 1
    assert all(chunk.section_title == "Large Section" for chunk in chunks)
    assert all(chunk.word_count <= 30 for chunk in chunks)


def test_chunks_do_not_contain_frontmatter() -> None:
    document = make_document(
        "---\n"
        'title: "Should Be Removed"\n'
        "---\n\n"
        "# Clean Body\n\nUseful content."
    )

    chunks = chunk_document(document)

    assert chunks
    assert all("---" not in chunk.text for chunk in chunks)
    assert chunks[0].section_title == "Clean Body"


def test_empty_chunks_are_not_produced() -> None:
    document = make_document("# Empty-ish\n\n\n## Also Empty\n\n   \n")

    chunks = chunk_document(document)

    assert chunks == []
