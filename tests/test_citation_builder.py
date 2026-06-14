from dataclasses import asdict

from app.context_engine.citation_builder import CitationBuilder
from app.schemas import RerankedResult


def make_chunk(chunk_id: str, title: str) -> RerankedResult:
    return RerankedResult(
        chunk_id=chunk_id,
        document_id=title.lower().replace(" ", "-"),
        document_title=title,
        department="finance",
        access_level="finance",
        section_title="Purpose",
        text="secret text should not be copied into citation",
        original_score=1.0,
        rerank_score=1.0,
        final_score=1.0,
        retrieval_method="hybrid",
        metadata={"version": "1.0", "effective_date": "2026-01-01"},
    )


def test_source_ids_start_at_one() -> None:
    citations = CitationBuilder().build([make_chunk("a", "A"), make_chunk("b", "B")])

    assert [citation.source_id for citation in citations] == [1, 2]


def test_citation_order_matches_chunk_order() -> None:
    citations = CitationBuilder().build([make_chunk("b", "B"), make_chunk("a", "A")])

    assert [citation.chunk_id for citation in citations] == ["b", "a"]


def test_metadata_fields_are_preserved() -> None:
    citation = CitationBuilder().build([make_chunk("a", "Invoice Approval Policy")])[0]

    assert citation.document_title == "Invoice Approval Policy"
    assert citation.version == "1.0"
    assert citation.effective_date == "2026-01-01"
    assert citation.retrieval_method == "hybrid"


def test_text_is_not_included_in_citation() -> None:
    citation = CitationBuilder().build([make_chunk("a", "Invoice Approval Policy")])[0]

    assert "text" not in asdict(citation)
    assert "secret text" not in str(citation)


def test_citation_builder_is_deterministic() -> None:
    chunks = [make_chunk("a", "A"), make_chunk("b", "B")]

    assert CitationBuilder().build(chunks) == CitationBuilder().build(chunks)
