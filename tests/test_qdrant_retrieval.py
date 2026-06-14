import pytest

pytest.importorskip("qdrant_client")

from app.retrieval.dense_retriever import FakeEmbeddingModel
from app.retrieval.qdrant_retriever import QdrantDenseRetriever
from app.schemas import Chunk


def make_chunks() -> list[Chunk]:
    return [
        Chunk(
            chunk_id="engineering-rollback::chunk_0001",
            document_id="engineering-rollback",
            document_title="Rollback Procedure",
            department="engineering",
            access_level="engineering",
            document_type="procedure",
            version="v1",
            effective_date="2026-01-01",
            section_title="Emergency Rollback Steps",
            text="Teams restore production after a bad release by coordinating rollback steps.",
            word_count=13,
            source_path="engineering-rollback.md",
        ),
        Chunk(
            chunk_id="hr-reimbursement::chunk_0001",
            document_id="hr-reimbursement",
            document_title="Reimbursement Policy",
            department="hr",
            access_level="hr",
            document_type="policy",
            version="v1",
            effective_date="2026-01-01",
            section_title="Eligible Expenses",
            text="Employees submit travel costs for reimbursement with receipts and approval.",
            word_count=10,
            source_path="hr-reimbursement.md",
        ),
        Chunk(
            chunk_id="legal-nda::chunk_0001",
            document_id="legal-nda",
            document_title="NDA Policy",
            department="legal",
            access_level="legal",
            document_type="policy",
            version="v1",
            effective_date="2026-01-01",
            section_title="Confidentiality Agreement Rules",
            text="Confidentiality agreement rules define non disclosure handling.",
            word_count=8,
            source_path="legal-nda.md",
        ),
    ]


def make_retriever() -> QdrantDenseRetriever:
    retriever = QdrantDenseRetriever(
        collection_name="test_enterprise_context_chunks",
        embedding_model=FakeEmbeddingModel(),
        url=":memory:",
    )
    retriever.build_index(make_chunks())
    return retriever


def test_qdrant_search_returns_results() -> None:
    retriever = make_retriever()

    results = retriever.search("how do we restore production after a bad release", top_k=2)

    assert results
    assert results[0].document_title == "Rollback Procedure"


def test_qdrant_search_uses_qdrant_retrieval_method() -> None:
    retriever = make_retriever()

    results = retriever.search("confidentiality agreement rules", top_k=1)

    assert results[0].retrieval_method == "qdrant_dense"


def test_qdrant_preserves_metadata_payload() -> None:
    retriever = make_retriever()

    result = retriever.search("travel reimbursement", top_k=1)[0]

    assert result.metadata["document_type"] == "policy"
    assert result.metadata["version"] == "v1"
    assert result.metadata["source_path"] == "hr-reimbursement.md"
    assert result.metadata["chunk_id"] == result.chunk_id


def test_qdrant_department_filter_works() -> None:
    retriever = make_retriever()

    results = retriever.search(
        "policy rules",
        top_k=3,
        filters={"department": "legal"},
    )

    assert results
    assert {result.department for result in results} == {"legal"}


def test_qdrant_query_order_is_deterministic() -> None:
    retriever = make_retriever()

    first = [result.chunk_id for result in retriever.search("paid back travel costs", top_k=3)]
    second = [result.chunk_id for result in retriever.search("paid back travel costs", top_k=3)]

    assert first == second


def test_qdrant_clear_removes_index() -> None:
    retriever = make_retriever()

    retriever.clear()

    with pytest.raises(RuntimeError, match="build_index"):
        retriever.search("travel reimbursement", top_k=1)
