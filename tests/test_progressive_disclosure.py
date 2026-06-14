from app.context_engine.progressive_disclosure import ProgressiveDisclosureEngine
from app.ingestion.pipeline import ingest_directory
from scripts.create_sample_docs import create_sample_docs


def build_engine_and_chunks(tmp_path):
    create_sample_docs(tmp_path)
    _, chunks = ingest_directory(tmp_path)
    return ProgressiveDisclosureEngine(), chunks


def test_progressive_disclosure_returns_result_structure(tmp_path) -> None:
    engine, chunks = build_engine_and_chunks(tmp_path)

    result = engine.run("What is the invoice approval limit?", chunks=chunks)

    assert result.retrieval_plan
    assert result.candidate_documents
    assert result.candidate_sections
    assert result.focused_chunks
    assert result.debug


def test_finance_query_returns_invoice_related_focused_chunks(tmp_path) -> None:
    engine, chunks = build_engine_and_chunks(tmp_path)

    result = engine.run("What is the invoice approval limit?", chunks=chunks)

    assert any(
        chunk.department == "finance" or "invoice" in chunk.document_title.lower()
        for chunk in result.focused_chunks
    )


def test_procedure_query_discovers_engineering_docs(tmp_path) -> None:
    engine, chunks = build_engine_and_chunks(tmp_path)

    result = engine.run("How do we restore production after a bad release?", chunks=chunks)
    document_titles = {
        item.document_title for item in result.candidate_documents
    } | {chunk.document_title for chunk in result.focused_chunks}

    assert any(
        title in {"Rollback Procedure", "Deployment Guide", "Production Access Policy"}
        for title in document_titles
    )
    assert any(chunk.department == "engineering" for chunk in result.focused_chunks)


def test_metadata_lookup_uses_department_filter(tmp_path) -> None:
    engine, chunks = build_engine_and_chunks(tmp_path)

    result = engine.run("Show documents in finance", chunks=chunks)

    assert result.retrieval_plan.retrieval_mode == "metadata_lookup"
    assert result.candidate_documents
    assert all(document.department == "finance" for document in result.candidate_documents)


def test_section_lookup_returns_retention_or_legal_content(tmp_path) -> None:
    engine, chunks = build_engine_and_chunks(tmp_path)

    result = engine.run("What section explains data retention?", chunks=chunks)

    assert result.retrieval_plan.retrieval_mode == "section_lookup"
    assert any(
        "retention" in section.section_title.lower() or section.department == "legal"
        for section in result.candidate_sections
    )
    assert any(
        "retention" in chunk.document_title.lower()
        or "retention" in chunk.section_title.lower()
        or chunk.department == "legal"
        for chunk in result.focused_chunks
    )


def test_top_k_is_respected(tmp_path) -> None:
    engine, chunks = build_engine_and_chunks(tmp_path)

    result = engine.run("What is the invoice approval limit?", chunks=chunks, top_k=3)

    assert len(result.focused_chunks) <= 3
    assert result.retrieval_plan.top_k == 3


def test_progressive_disclosure_is_deterministic(tmp_path) -> None:
    engine, chunks = build_engine_and_chunks(tmp_path)

    first = engine.run("NDA policy", chunks=chunks)
    second = engine.run("NDA policy", chunks=chunks)

    assert [chunk.chunk_id for chunk in first.focused_chunks] == [
        chunk.chunk_id for chunk in second.focused_chunks
    ]


def test_debug_fields_exist(tmp_path) -> None:
    engine, chunks = build_engine_and_chunks(tmp_path)

    result = engine.run("Compare remote work policy and contractor policy", chunks=chunks)

    assert {
        "retrieval_mode",
        "intent",
        "candidate_document_count",
        "candidate_section_count",
        "focused_chunk_count",
        "progressive_disclosure",
    }.issubset(result.debug)
    assert result.debug["progressive_disclosure"] is True
