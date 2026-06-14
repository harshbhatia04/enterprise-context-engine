import pytest

from app.ingestion.pipeline import ingest_directory
from app.retrieval.bm25_retriever import BM25Retriever
from app.retrieval.dense_retriever import DenseRetriever, FakeEmbeddingModel
from app.retrieval.hybrid_retriever import HybridRetriever
from scripts.create_sample_docs import create_sample_docs


def build_hybrid_retriever(tmp_path, alpha: float = 0.5) -> HybridRetriever:
    create_sample_docs(tmp_path)
    _, chunks = ingest_directory(tmp_path)
    bm25 = BM25Retriever()
    bm25.build_index(chunks)
    dense = DenseRetriever(FakeEmbeddingModel())
    dense.build_index(chunks)
    return HybridRetriever(bm25, dense, alpha=alpha)


def test_invalid_alpha_raises_value_error(tmp_path) -> None:
    create_sample_docs(tmp_path)
    _, chunks = ingest_directory(tmp_path)
    bm25 = BM25Retriever()
    bm25.build_index(chunks)
    dense = DenseRetriever(FakeEmbeddingModel())
    dense.build_index(chunks)

    with pytest.raises(ValueError, match="alpha"):
        HybridRetriever(bm25, dense, alpha=1.5)


def test_hybrid_returns_results(tmp_path) -> None:
    retriever = build_hybrid_retriever(tmp_path)

    results = retriever.search("invoice approval limit", top_k=5)

    assert results
    assert results[0].retrieval_method == "hybrid"


def test_hybrid_metadata_contains_component_scores(tmp_path) -> None:
    retriever = build_hybrid_retriever(tmp_path)

    result = retriever.search("invoice approval limit", top_k=1)[0]

    assert {
        "bm25_score",
        "dense_score",
        "normalized_bm25_score",
        "normalized_dense_score",
        "alpha",
    }.issubset(result.metadata)
    assert result.normalized_score == result.score


def test_hybrid_deduplicates_chunks(tmp_path) -> None:
    retriever = build_hybrid_retriever(tmp_path)

    results = retriever.search("invoice approval limit", top_k=10, candidate_k=20)
    chunk_ids = [result.chunk_id for result in results]

    assert len(chunk_ids) == len(set(chunk_ids))


def test_hybrid_exact_query_retrieves_invoice_policy(tmp_path) -> None:
    retriever = build_hybrid_retriever(tmp_path)

    results = retriever.search("invoice approval limit", top_k=5)

    assert results
    assert any(result.document_title == "Invoice Approval Policy" for result in results)


def test_hybrid_paraphrased_query_retrieves_reimbursement_policy(tmp_path) -> None:
    retriever = build_hybrid_retriever(tmp_path, alpha=0.7)

    results = retriever.search("how do we get paid back for travel costs", top_k=5)

    assert results
    assert any(
        result.document_title == "Reimbursement Policy" or "expense" in result.text.lower()
        for result in results
    )


def test_hybrid_order_is_deterministic(tmp_path) -> None:
    retriever = build_hybrid_retriever(tmp_path)

    first = [result.chunk_id for result in retriever.search("confidentiality agreement rules", top_k=5)]
    second = [result.chunk_id for result in retriever.search("confidentiality agreement rules", top_k=5)]

    assert first == second


def test_hybrid_top_k_is_respected(tmp_path) -> None:
    retriever = build_hybrid_retriever(tmp_path)

    results = retriever.search("remote work policy", top_k=3)

    assert 0 < len(results) <= 3
