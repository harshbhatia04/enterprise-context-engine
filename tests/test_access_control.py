import pytest

from app.context_engine.progressive_disclosure import SecureProgressiveDisclosureEngine
from app.ingestion.pipeline import ingest_directory
from app.security.access_control import AccessController, SAFE_ABSTAIN_MESSAGE
from scripts.create_sample_docs import create_sample_docs


def build_secure_engine_and_chunks(tmp_path):
    create_sample_docs(tmp_path)
    _, chunks = ingest_directory(tmp_path)
    return SecureProgressiveDisclosureEngine(), chunks


def assert_chunks_have_allowed_levels(result, allowed_levels: set[str]) -> None:
    assert result.focused_chunks
    assert all(chunk.access_level.lower() in allowed_levels for chunk in result.focused_chunks)


def test_user_permission_levels() -> None:
    controller = AccessController()

    assert {"finance", "hr", "engineering", "legal"}.issubset(
        set(controller.get_allowed_access_levels("admin_user"))
    )
    assert set(controller.get_allowed_access_levels("intern_user")) == {"public", "general"}
    finance_levels = set(controller.get_allowed_access_levels("finance_user"))
    assert {"finance", "public", "general"}.issubset(finance_levels)
    assert "legal" not in finance_levels


def test_finance_user_can_access_finance_result(tmp_path) -> None:
    engine, chunks = build_secure_engine_and_chunks(tmp_path)

    result = engine.run("What is the invoice approval limit?", "finance_user", chunks=chunks)

    assert result.safe_abstain is False
    assert_chunks_have_allowed_levels(result, {"finance", "public", "general"})
    assert any(
        "Invoice" in chunk.document_title or chunk.department == "finance"
        for chunk in result.focused_chunks
    )


def test_intern_cannot_access_finance_result_without_leak(tmp_path) -> None:
    engine, chunks = build_secure_engine_and_chunks(tmp_path)

    result = engine.run("What is the invoice approval limit?", "intern_user", chunks=chunks)

    assert result.safe_abstain is True
    assert result.safe_message == SAFE_ABSTAIN_MESSAGE
    assert result.candidate_documents == []
    assert result.candidate_sections == []
    assert result.focused_chunks == []
    assert "Invoice Approval Policy" not in str(result.debug)
    assert "Invoice Approval Policy" not in str(result.access_filter_result.debug)
    assert set(result.debug) == {
        "user_id",
        "allowed_access_levels",
        "candidate_documents_before",
        "candidate_documents_after",
        "candidate_sections_before",
        "candidate_sections_after",
        "focused_chunks_before",
        "focused_chunks_after",
        "filtered_document_count",
        "filtered_section_count",
        "filtered_chunk_count",
        "retrieval_mode",
        "intent",
        "safe_abstain",
    }
    assert result.debug["retrieval_mode"] == "hybrid"
    assert result.debug["intent"] == "exact_lookup"


def test_engineer_can_access_engineering_result(tmp_path) -> None:
    engine, chunks = build_secure_engine_and_chunks(tmp_path)

    result = engine.run(
        "How do we restore production after a bad release?",
        "engineer_user",
        chunks=chunks,
    )

    assert result.safe_abstain is False
    assert_chunks_have_allowed_levels(result, {"engineering", "public", "general"})
    assert any(
        chunk.department == "engineering"
        or chunk.document_title in {"Rollback Procedure", "Deployment Guide"}
        for chunk in result.focused_chunks
    )


def test_hr_cannot_access_engineering_result_without_leak(tmp_path) -> None:
    engine, chunks = build_secure_engine_and_chunks(tmp_path)

    result = engine.run(
        "How do we restore production after a bad release?",
        "hr_user",
        chunks=chunks,
    )

    assert result.safe_abstain is True
    assert result.focused_chunks == []
    assert result.candidate_documents == []
    assert "Rollback Procedure" not in str(result.debug)
    assert "Deployment Guide" not in str(result.debug)
    assert "engineering" not in str(result.debug).lower()


def test_admin_can_access_legal_result(tmp_path) -> None:
    engine, chunks = build_secure_engine_and_chunks(tmp_path)

    result = engine.run("NDA policy", "admin_user", chunks=chunks)

    assert result.safe_abstain is False
    assert result.focused_chunks
    assert any(chunk.department == "legal" for chunk in result.focused_chunks)


def test_intern_cannot_access_legal_result_without_leak(tmp_path) -> None:
    engine, chunks = build_secure_engine_and_chunks(tmp_path)

    result = engine.run("NDA policy", "intern_user", chunks=chunks)

    assert result.safe_abstain is True
    assert result.safe_message == SAFE_ABSTAIN_MESSAGE
    assert result.focused_chunks == []
    assert result.candidate_documents == []
    assert result.candidate_sections == []
    assert "NDA Policy" not in str(result.debug)
    assert "legal" not in str(result.debug).lower()


def test_unknown_user_raises_value_error(tmp_path) -> None:
    engine, chunks = build_secure_engine_and_chunks(tmp_path)

    with pytest.raises(ValueError, match="Unknown user_id"):
        engine.run("NDA policy", "missing_user", chunks=chunks)


def test_filtering_is_deterministic(tmp_path) -> None:
    engine, chunks = build_secure_engine_and_chunks(tmp_path)

    first = engine.run("What is the invoice approval limit?", "finance_user", chunks=chunks)
    second = engine.run("What is the invoice approval limit?", "finance_user", chunks=chunks)

    assert [chunk.chunk_id for chunk in first.focused_chunks] == [
        chunk.chunk_id for chunk in second.focused_chunks
    ]
