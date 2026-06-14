from app.context_engine.context_builder import ContextBuilder, build_secure_context
from app.ingestion.pipeline import ingest_directory
from app.security.access_control import SAFE_ABSTAIN_MESSAGE
from app.schemas import RerankedResult
from scripts.create_sample_docs import create_sample_docs


def make_chunk(
    chunk_id: str,
    title: str,
    text: str = "invoice approval limit details",
    score: float = 1.0,
) -> RerankedResult:
    return RerankedResult(
        chunk_id=chunk_id,
        document_id=title.lower().replace(" ", "-"),
        document_title=title,
        department="finance",
        access_level="finance",
        section_title="Approval Limits",
        text=text,
        original_score=score,
        rerank_score=score,
        final_score=score,
        retrieval_method="hybrid",
        metadata={"version": "1.0", "effective_date": "2026-01-01"},
    )


def test_builds_context_with_source_markers() -> None:
    result = ContextBuilder().build(
        "invoice approval",
        [make_chunk("one", "Invoice Approval Policy"), make_chunk("two", "Budget Approval Workflow")],
    )

    assert "[1]" in result.context_text
    assert "[2]" in result.context_text
    assert "Document: Invoice Approval Policy" in result.context_text


def test_citation_count_equals_included_chunk_count() -> None:
    result = ContextBuilder().build(
        "invoice approval",
        [make_chunk("one", "Invoice Approval Policy"), make_chunk("two", "Budget Approval Workflow")],
    )

    assert len(result.citations) == len(result.included_chunks)


def test_respects_max_context_words() -> None:
    chunks = [
        make_chunk(f"chunk-{index}", f"Doc {index}", text=" ".join(["word"] * 20))
        for index in range(10)
    ]

    result = ContextBuilder(max_context_words=80, max_chunk_words=20).build("word", chunks)

    assert result.debug["context_word_count"] <= 80


def test_truncates_long_chunks() -> None:
    long_text = " ".join(f"word{index}" for index in range(40))

    result = ContextBuilder(max_context_words=200, max_chunk_words=10).build(
        "word",
        [make_chunk("one", "Invoice Approval Policy", text=long_text)],
    )

    assert result.debug["truncated_chunks"] == 1
    assert "word10" not in result.context_text


def test_safe_abstain_returns_empty_context_and_citations() -> None:
    result = ContextBuilder().build(
        "invoice approval",
        [make_chunk("one", "Invoice Approval Policy")],
        safe_abstain=True,
        safe_message=SAFE_ABSTAIN_MESSAGE,
    )

    assert result.safe_abstain is True
    assert result.context_text == ""
    assert result.citations == []
    assert result.included_chunks == []


def test_empty_chunks_returns_safe_abstain() -> None:
    result = ContextBuilder().build("invoice approval", [])

    assert result.safe_abstain is True
    assert result.safe_message == SAFE_ABSTAIN_MESSAGE


def test_context_text_omits_internal_metadata_and_debug_fields() -> None:
    result = ContextBuilder().build("invoice approval", [make_chunk("one", "Invoice Approval Policy")])

    assert "chunk_id" not in result.context_text
    assert "retrieval_method" not in result.context_text
    assert "debug" not in result.context_text.lower()


def test_context_does_not_duplicate_chunks() -> None:
    chunk = make_chunk("one", "Invoice Approval Policy")

    result = ContextBuilder().build("invoice approval", [chunk, chunk])

    assert len(result.included_chunks) == 1
    assert result.context_text.count("[1]") == 1


def test_build_secure_context_returns_context_for_authorized_user(tmp_path) -> None:
    create_sample_docs(tmp_path)
    _, chunks = ingest_directory(tmp_path)

    result = build_secure_context(
        "What is the invoice approval limit?",
        "finance_user",
        chunks,
        top_k=5,
    )

    assert result.safe_abstain is False
    assert result.context_text
    assert result.citations
    assert "Invoice Approval Policy" in result.context_text


def test_build_secure_context_safe_abstains_without_leaking_for_unauthorized_user(tmp_path) -> None:
    create_sample_docs(tmp_path)
    _, chunks = ingest_directory(tmp_path)

    result = build_secure_context(
        "What is the invoice approval limit?",
        "intern_user",
        chunks,
        top_k=5,
    )

    assert result.safe_abstain is True
    assert result.context_text == ""
    assert result.citations == []
    assert "Invoice Approval Policy" not in str(result.debug)
    assert "invoice-approval-policy" not in str(result.debug)
