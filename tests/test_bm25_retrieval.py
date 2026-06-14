import pytest

from app.ingestion.pipeline import ingest_directory
from app.retrieval.bm25_retriever import BM25Retriever, tokenize
from scripts.create_sample_docs import create_sample_docs


def build_sample_retriever(tmp_path):
    create_sample_docs(tmp_path)
    _, chunks = ingest_directory(tmp_path)
    retriever = BM25Retriever()
    retriever.build_index(chunks)
    return retriever


def test_tokenizer_keeps_enterprise_terms() -> None:
    assert tokenize("Invoice approval limit?") == ["invoice", "approval", "limit"]
    assert tokenize("rollback-procedure") == ["rollback", "procedure"]
    assert tokenize("NDA v2.0") == ["nda", "v2", "0"]


def test_search_before_index_raises_clear_error() -> None:
    retriever = BM25Retriever()

    with pytest.raises(RuntimeError, match="build_index"):
        retriever.search("invoice approval")


def test_exact_finance_retrieval(tmp_path) -> None:
    retriever = build_sample_retriever(tmp_path)

    results = retriever.search("invoice approval", top_k=5)

    assert results
    assert any(
        "Invoice Approval" in result.document_title or result.department == "finance"
        for result in results
    )
    assert results[0].retrieval_method == "bm25"


def test_engineering_retrieval(tmp_path) -> None:
    retriever = build_sample_retriever(tmp_path)

    results = retriever.search("failed deployment rollback", top_k=5)

    assert results
    assert any(
        result.document_title == "Rollback Procedure" or result.department == "engineering"
        for result in results
    )


def test_legal_retrieval(tmp_path) -> None:
    retriever = build_sample_retriever(tmp_path)

    results = retriever.search("NDA policy", top_k=5)

    assert results
    assert any("NDA" in result.document_title or result.department == "legal" for result in results)


def test_exact_retention_query_prefers_retention_policy(tmp_path) -> None:
    retriever = build_sample_retriever(tmp_path)

    results = retriever.search("data retention requirements", top_k=3)

    assert results
    assert results[0].document_title == "Retention Policy"


def test_retrieval_order_is_deterministic(tmp_path) -> None:
    retriever = build_sample_retriever(tmp_path)

    first = [result.chunk_id for result in retriever.search("remote work policy", top_k=5)]
    second = [result.chunk_id for result in retriever.search("remote work policy", top_k=5)]

    assert first == second


def test_top_k_limits_results(tmp_path) -> None:
    retriever = build_sample_retriever(tmp_path)

    results = retriever.search("vendor payment approval", top_k=3)

    assert 0 < len(results) <= 3
