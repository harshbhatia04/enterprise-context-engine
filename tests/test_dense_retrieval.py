import pytest

from app.ingestion.pipeline import ingest_directory
from app.retrieval.dense_retriever import DenseRetriever, FakeEmbeddingModel, create_dense_retriever
from scripts.create_sample_docs import create_sample_docs


def build_dense_retriever(tmp_path):
    create_sample_docs(tmp_path)
    _, chunks = ingest_directory(tmp_path)
    retriever = DenseRetriever(FakeEmbeddingModel())
    retriever.build_index(chunks)
    return retriever


def test_search_before_dense_index_raises_clear_error() -> None:
    retriever = DenseRetriever(FakeEmbeddingModel())

    with pytest.raises(RuntimeError, match="build_index"):
        retriever.search("restore production")


def test_dense_retrieval_returns_results(tmp_path) -> None:
    retriever = build_dense_retriever(tmp_path)

    results = retriever.search("invoice approval", top_k=5)

    assert results
    assert results[0].retrieval_method == "dense"


def test_dense_paraphrased_query_retrieves_engineering_document(tmp_path) -> None:
    retriever = build_dense_retriever(tmp_path)

    results = retriever.search("how do we restore production after a bad release", top_k=5)

    assert results
    assert any(
        result.document_title in {"Rollback Procedure", "Deployment Guide"}
        or result.department == "engineering"
        for result in results
    )


def test_dense_order_is_deterministic(tmp_path) -> None:
    retriever = build_dense_retriever(tmp_path)

    first = [result.chunk_id for result in retriever.search("work from home guidelines", top_k=5)]
    second = [result.chunk_id for result in retriever.search("work from home guidelines", top_k=5)]

    assert first == second


def test_dense_top_k_is_respected(tmp_path) -> None:
    retriever = build_dense_retriever(tmp_path)

    results = retriever.search("confidentiality agreement rules", top_k=3)

    assert 0 < len(results) <= 3


def test_create_dense_retriever_defaults_to_memory_backend() -> None:
    retriever = create_dense_retriever("memory", FakeEmbeddingModel())

    assert isinstance(retriever, DenseRetriever)
