import pytest

from app.evaluation.metrics import (
    abstention_correct,
    citation_presence,
    department_hit,
    document_hit,
    grounded_answer_heuristic,
    mrr,
    ndcg_at_k,
    normalize_text,
    recall_at_k,
    restricted_leak_detected,
    safe_divide,
)
from app.schemas import Citation
from app.security.access_control import SAFE_ABSTAIN_MESSAGE


def make_citation() -> Citation:
    return Citation(
        source_id=1,
        chunk_id="chunk-1",
        document_id="doc-1",
        document_title="Invoice Approval Policy",
        department="finance",
        section_title="Approval Limits",
        access_level="finance",
    )


def test_normalize_text_lowercases_trims_and_collapses_whitespace() -> None:
    assert normalize_text("  Invoice   Approval\nPolicy  ") == "invoice approval policy"


def test_document_hit_exact_and_substring() -> None:
    assert document_hit(["Invoice Approval Policy"], ["Invoice Approval Policy"]) is True
    assert document_hit(["Finance Invoice Approval Policy v1"], ["Invoice Approval Policy"]) is True
    assert document_hit(["Vendor Payment Policy"], ["Invoice Approval Policy"]) is False


def test_department_hit_matches_normalized_department() -> None:
    assert department_hit(["Finance"], ["finance"]) is True
    assert department_hit(["engineering"], ["finance"]) is False


def test_recall_at_k_uses_expected_document_titles() -> None:
    retrieved = ["Invoice Approval Policy", "Vendor Payment Policy"]
    expected = ["Invoice Approval Policy", "Budget Approval Workflow"]

    assert recall_at_k(retrieved, expected, 1) == 0.5


def test_mrr_returns_reciprocal_rank_of_first_hit() -> None:
    retrieved = ["Vendor Payment Policy", "Invoice Approval Policy"]

    assert mrr(retrieved, ["Invoice Approval Policy"]) == 0.5
    assert mrr(retrieved, ["Missing Policy"]) == 0.0


def test_ndcg_at_k_scores_ranked_binary_relevance() -> None:
    assert ndcg_at_k(["Invoice Approval Policy"], ["Invoice Approval Policy"], 5) == 1.0
    assert ndcg_at_k(["Vendor Payment Policy", "Invoice Approval Policy"], ["Invoice Approval Policy"], 5) == pytest.approx(0.6309, rel=1e-3)


def test_citation_presence_for_answer_and_abstention() -> None:
    assert citation_presence("Use the policy [1].", 1, should_abstain=False) is True
    assert citation_presence("Use the policy.", 1, should_abstain=False) is False
    assert citation_presence(SAFE_ABSTAIN_MESSAGE, 0, should_abstain=True) is True
    assert citation_presence(SAFE_ABSTAIN_MESSAGE, 1, should_abstain=True) is False


def test_abstention_correct() -> None:
    assert abstention_correct(True, True) is True
    assert abstention_correct(False, True) is False


def test_restricted_leak_detected_uses_normalized_substrings() -> None:
    assert restricted_leak_detected("The NDA Policy applies.", ["nda policy"]) is True
    assert restricted_leak_detected("No accessible documents were found.", ["nda policy"]) is False


def test_grounded_answer_heuristic_for_answer_and_abstention() -> None:
    assert grounded_answer_heuristic("Use approval details [1].", [make_citation()], False) is True
    assert grounded_answer_heuristic("", [make_citation()], False) is False
    assert grounded_answer_heuristic(SAFE_ABSTAIN_MESSAGE, [], True) is True
    assert grounded_answer_heuristic("No.", [make_citation()], True) is False


def test_safe_divide_handles_zero_denominator() -> None:
    assert safe_divide(3, 2) == 1.5
    assert safe_divide(3, 0) == 0.0
