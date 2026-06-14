from app.context_engine.evidence_gate import EvidenceGate
from app.schemas import Citation, ContextBuildResult, RerankedResult
from app.security.access_control import SAFE_ABSTAIN_MESSAGE


def make_context(
    *,
    title: str = "Remote Work Handbook",
    section: str = "Remote Work Practices",
    text: str = "Remote work uses asynchronous documentation and clear availability norms.",
    safe_abstain: bool = False,
    final_score: float = 0.8,
) -> ContextBuildResult:
    if safe_abstain:
        return ContextBuildResult(
            query="question",
            context_text="",
            citations=[],
            included_chunks=[],
            safe_abstain=True,
            safe_message=SAFE_ABSTAIN_MESSAGE,
        )
    chunk = RerankedResult(
        chunk_id="chunk-1",
        document_id="doc-1",
        document_title=title,
        department="hr",
        access_level="public",
        section_title=section,
        text=text,
        original_score=final_score,
        rerank_score=final_score,
        final_score=final_score,
        retrieval_method="hybrid",
    )
    citation = Citation(
        source_id=1,
        chunk_id=chunk.chunk_id,
        document_id=chunk.document_id,
        document_title=chunk.document_title,
        department=chunk.department,
        section_title=chunk.section_title,
        access_level=chunk.access_level,
        score=chunk.final_score,
    )
    return ContextBuildResult(
        query="question",
        context_text=(
            f"[1]\nDocument: {title}\nSection: {section}\nText:\n{text}"
        ),
        citations=[citation],
        included_chunks=[chunk],
        safe_abstain=False,
    )


def test_empty_context_is_unsupported() -> None:
    decision = EvidenceGate().evaluate(
        "What does the handbook say about remote work?",
        ContextBuildResult(
            query="question",
            context_text="",
            citations=[],
            included_chunks=[],
            safe_abstain=False,
        ),
    )

    assert decision.is_supported is False
    assert decision.confidence_score == 0.0


def test_safe_abstain_context_is_unsupported() -> None:
    decision = EvidenceGate().evaluate("remote work", make_context(safe_abstain=True))

    assert decision.is_supported is False
    assert decision.reason == "context builder already safe-abstained"


def test_matching_title_and_text_support_query() -> None:
    decision = EvidenceGate().evaluate(
        "What does the handbook say about remote work?",
        make_context(),
    )

    assert decision.is_supported is True
    assert "remote" in decision.matched_terms
    assert "work" in decision.matched_terms


def test_generic_only_match_does_not_support_query() -> None:
    decision = EvidenceGate().evaluate(
        "What is the company policy document?",
        make_context(title="Company Policy Handbook", section="Policy", text="Company policy text."),
    )

    assert decision.is_supported is False
    assert decision.matched_terms == []


def test_cafeteria_lunch_query_is_unsupported_against_remote_work() -> None:
    decision = EvidenceGate().evaluate(
        "What is the company's cafeteria lunch menu?",
        make_context(),
    )

    assert decision.is_supported is False
    assert decision.matched_terms == []
    assert {"cafeteria", "lunch", "menu"}.issubset(set(decision.missing_terms))


def test_remote_work_query_is_supported_against_remote_work() -> None:
    decision = EvidenceGate().evaluate(
        "What does the handbook say about remote work?",
        make_context(),
    )

    assert decision.is_supported is True
    assert decision.confidence_score >= 0.25


def test_acquisition_plan_query_is_unsupported_against_unrelated_handbook() -> None:
    decision = EvidenceGate().evaluate(
        "What is the unreleased acquisition plan?",
        make_context(),
    )

    assert decision.is_supported is False
    assert {"unreleased", "acquisition"}.issubset(set(decision.missing_terms))


def test_decision_is_deterministic() -> None:
    gate = EvidenceGate()
    context = make_context()

    first = gate.evaluate("What does the handbook say about remote work?", context)
    second = gate.evaluate("What does the handbook say about remote work?", context)

    assert first == second


def test_debug_includes_matched_and_missing_terms() -> None:
    decision = EvidenceGate().evaluate(
        "remote cafeteria work",
        make_context(),
    )

    assert "matched_terms" in decision.debug
    assert "missing_terms" in decision.debug
    assert "remote" in decision.debug["matched_terms"]
    assert "cafeteria" in decision.debug["missing_terms"]
