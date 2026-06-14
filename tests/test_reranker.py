from app.retrieval.reranker import FakeReranker
from app.schemas import RetrievalResult


def make_result(
    chunk_id: str,
    title: str,
    section: str,
    text: str,
    score: float,
    department: str = "finance",
) -> RetrievalResult:
    return RetrievalResult(
        chunk_id=chunk_id,
        document_id=title.lower().replace(" ", "-"),
        document_title=title,
        department=department,
        access_level=department,
        section_title=section,
        text=text,
        score=score,
        retrieval_method="hybrid",
        metadata={
            "version": "1.0",
            "effective_date": "2026-01-01",
            "document_type": "policy",
        },
    )


def test_empty_results_return_empty_list() -> None:
    assert FakeReranker().rerank("invoice approval", []) == []


def test_reranker_deduplicates_duplicate_chunk_ids() -> None:
    first = make_result("same", "Invoice Approval Policy", "Purpose", "invoice approval", 1.0)
    duplicate = make_result("same", "Invoice Approval Policy", "Purpose", "invoice approval", 0.5)

    reranked = FakeReranker().rerank("invoice approval", [first, duplicate], top_k=5)

    assert len(reranked) == 1
    assert reranked[0].chunk_id == "same"


def test_reranker_respects_top_k() -> None:
    results = [
        make_result(f"chunk-{index}", f"Doc {index}", "Purpose", "invoice approval", 1.0)
        for index in range(5)
    ]

    assert len(FakeReranker().rerank("invoice approval", results, top_k=3)) == 3


def test_reranker_order_is_deterministic() -> None:
    results = [
        make_result("a", "Invoice Approval Policy", "Purpose", "invoice approval", 1.0),
        make_result("b", "Budget Approval Workflow", "Purpose", "approval", 0.8),
    ]

    first = [item.chunk_id for item in FakeReranker().rerank("invoice approval", results)]
    second = [item.chunk_id for item in FakeReranker().rerank("invoice approval", results)]

    assert first == second


def test_query_relevant_result_ranks_above_irrelevant_result() -> None:
    relevant = make_result(
        "relevant",
        "Invoice Approval Policy",
        "Approval Limits",
        "invoice approval limit and policy details",
        0.2,
    )
    irrelevant = make_result(
        "irrelevant",
        "Remote Work Policy",
        "Eligibility",
        "workspace expectations and remote work",
        0.1,
        department="hr",
    )

    reranked = FakeReranker().rerank("invoice approval limit", [irrelevant, relevant])

    assert reranked[0].chunk_id == "relevant"


def test_metadata_is_preserved() -> None:
    result = make_result("one", "Invoice Approval Policy", "Purpose", "invoice approval", 1.0)

    reranked = FakeReranker().rerank("invoice approval", [result])[0]

    assert reranked.metadata["version"] == "1.0"
    assert reranked.metadata["effective_date"] == "2026-01-01"


def test_reranked_result_includes_scores() -> None:
    result = make_result("one", "Invoice Approval Policy", "Purpose", "invoice approval", 1.0)

    reranked = FakeReranker().rerank("invoice approval", [result])[0]

    assert reranked.original_score == 1.0
    assert reranked.rerank_score >= 0.0
    assert reranked.final_score >= 0.0
