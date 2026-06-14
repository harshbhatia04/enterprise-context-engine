"""Hybrid retrieval with normalized BM25 and dense score fusion."""

from __future__ import annotations

from app.retrieval.bm25_retriever import BM25Retriever
from app.retrieval.dense_retriever import DenseRetriever
from app.schemas import RetrievalResult


def _normalize_scores(results: list[RetrievalResult]) -> dict[str, float]:
    if not results:
        return {}

    scores = [result.score for result in results]
    min_score = min(scores)
    max_score = max(scores)
    if max_score == min_score:
        value = 1.0 if max_score > 0.0 else 0.0
        return {result.chunk_id: value for result in results}

    return {
        result.chunk_id: (result.score - min_score) / (max_score - min_score)
        for result in results
    }


class HybridRetriever:
    """Combine BM25 and dense retrieval through normalized score fusion."""

    def __init__(
        self,
        bm25_retriever: BM25Retriever,
        dense_retriever: DenseRetriever,
        alpha: float = 0.5,
    ) -> None:
        if not 0.0 <= alpha <= 1.0:
            raise ValueError("alpha must be between 0.0 and 1.0")
        self.bm25_retriever = bm25_retriever
        self.dense_retriever = dense_retriever
        self.alpha = alpha

    def search(self, query: str, top_k: int = 5, candidate_k: int = 20) -> list[RetrievalResult]:
        """Return fused BM25+dense results for a query."""
        if top_k <= 0 or candidate_k <= 0:
            return []

        bm25_results = self.bm25_retriever.search(query, top_k=candidate_k)
        dense_results = self.dense_retriever.search(query, top_k=candidate_k)
        normalized_bm25 = _normalize_scores(bm25_results)
        normalized_dense = _normalize_scores(dense_results)

        merged: dict[str, RetrievalResult] = {}
        for result in bm25_results + dense_results:
            merged.setdefault(result.chunk_id, result)

        fused: list[RetrievalResult] = []
        bm25_by_id = {result.chunk_id: result.score for result in bm25_results}
        dense_by_id = {result.chunk_id: result.score for result in dense_results}

        for chunk_id, base_result in merged.items():
            norm_bm25 = normalized_bm25.get(chunk_id, 0.0)
            norm_dense = normalized_dense.get(chunk_id, 0.0)
            hybrid_score = (self.alpha * norm_dense) + ((1 - self.alpha) * norm_bm25)
            metadata = {
                **base_result.metadata,
                "bm25_score": bm25_by_id.get(chunk_id, 0.0),
                "dense_score": dense_by_id.get(chunk_id, 0.0),
                "normalized_bm25_score": norm_bm25,
                "normalized_dense_score": norm_dense,
                "alpha": self.alpha,
            }
            fused.append(
                RetrievalResult(
                    chunk_id=base_result.chunk_id,
                    document_id=base_result.document_id,
                    document_title=base_result.document_title,
                    department=base_result.department,
                    access_level=base_result.access_level,
                    section_title=base_result.section_title,
                    text=base_result.text,
                    score=hybrid_score,
                    retrieval_method="hybrid",
                    metadata=metadata,
                    normalized_score=hybrid_score,
                )
            )

        fused.sort(key=lambda result: (-result.score, result.document_title.lower(), result.chunk_id))
        return fused[:top_k]
