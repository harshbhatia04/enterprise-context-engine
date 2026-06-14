"""Optional reranking for accessible retrieval results."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.retrieval.bm25_retriever import tokenize
from app.schemas import RerankedResult, RetrievalResult


class BaseReranker(ABC):
    """Interface for reranking access-filtered retrieval results."""

    @abstractmethod
    def rerank(
        self,
        query: str,
        results: list[RetrievalResult],
        top_k: int = 5,
    ) -> list[RerankedResult]:
        """Return reranked results in descending relevance order."""


def _deduplicate_results(results: list[RetrievalResult]) -> list[RetrievalResult]:
    deduped: dict[str, RetrievalResult] = {}
    for result in results:
        current = deduped.get(result.chunk_id)
        if current is None or result.score > current.score:
            deduped[result.chunk_id] = result
    return list(deduped.values())


def _normalize(values: list[float]) -> list[float]:
    if not values:
        return []
    min_value = min(values)
    max_value = max(values)
    if max_value == min_value:
        return [1.0 if max_value > 0.0 else 0.0 for _ in values]
    return [(value - min_value) / (max_value - min_value) for value in values]


def _normalize_query(query: str) -> str:
    return " ".join(query.lower().strip().split())


def _to_reranked_result(
    result: RetrievalResult,
    rerank_score: float,
    final_score: float,
) -> RerankedResult:
    return RerankedResult(
        chunk_id=result.chunk_id,
        document_id=result.document_id,
        document_title=result.document_title,
        department=result.department,
        access_level=result.access_level,
        section_title=result.section_title,
        text=result.text,
        original_score=result.score,
        rerank_score=rerank_score,
        final_score=final_score,
        retrieval_method=result.retrieval_method,
        metadata=dict(result.metadata),
    )


class FakeReranker(BaseReranker):
    """Deterministic lexical reranker for tests and offline demos."""

    def rerank(
        self,
        query: str,
        results: list[RetrievalResult],
        top_k: int = 5,
    ) -> list[RerankedResult]:
        """Rerank by lexical overlap plus title/section boosts."""
        if top_k <= 0:
            return []
        deduped = _deduplicate_results(results)
        if not deduped:
            return []

        rerank_scores = [self._score(query, result) for result in deduped]
        normalized_original = _normalize([result.score for result in deduped])
        normalized_rerank = _normalize(rerank_scores)

        reranked = [
            _to_reranked_result(
                result,
                rerank_score=rerank_score,
                final_score=(0.6 * original_score) + (0.4 * normalized_score),
            )
            for result, rerank_score, original_score, normalized_score in zip(
                deduped,
                rerank_scores,
                normalized_original,
                normalized_rerank,
                strict=True,
            )
        ]
        reranked.sort(
            key=lambda item: (-item.final_score, item.document_title.lower(), item.chunk_id)
        )
        return reranked[:top_k]

    def _score(self, query: str, result: RetrievalResult) -> float:
        query_tokens = set(tokenize(query))
        if not query_tokens:
            return 0.0

        text_tokens = set(tokenize(result.text))
        title_tokens = set(tokenize(result.document_title))
        section_tokens = set(tokenize(result.section_title))
        lexical_overlap = len(query_tokens.intersection(text_tokens)) / len(query_tokens)
        title_boost = 0.8 * len(query_tokens.intersection(title_tokens))
        section_boost = 0.6 * len(query_tokens.intersection(section_tokens))

        department_boost = 0.0
        metadata_hint = str(result.metadata.get("department_hint", "")).lower()
        if metadata_hint and metadata_hint == result.department.lower():
            department_boost = 0.2
        elif _normalize_query(result.department) in _normalize_query(query):
            department_boost = 0.2

        return lexical_overlap + title_boost + section_boost + department_boost


class CrossEncoderReranker(BaseReranker):
    """Optional cross-encoder reranker loaded only when explicitly used."""

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2") -> None:
        self.model_name = model_name
        self._model = None

    def _load_model(self):
        if self._model is None:
            from sentence_transformers import CrossEncoder

            self._model = CrossEncoder(self.model_name)
        return self._model

    def rerank(
        self,
        query: str,
        results: list[RetrievalResult],
        top_k: int = 5,
    ) -> list[RerankedResult]:
        """Rerank retrieval results with a sentence-transformers CrossEncoder."""
        if top_k <= 0:
            return []
        deduped = _deduplicate_results(results)
        if not deduped:
            return []

        model = self._load_model()
        pairs = [(query, result.text) for result in deduped]
        raw_scores = [float(score) for score in model.predict(pairs)]
        normalized_original = _normalize([result.score for result in deduped])
        normalized_rerank = _normalize(raw_scores)

        reranked = [
            _to_reranked_result(
                result,
                rerank_score=rerank_score,
                final_score=(0.6 * original_score) + (0.4 * normalized_score),
            )
            for result, rerank_score, original_score, normalized_score in zip(
                deduped,
                raw_scores,
                normalized_original,
                normalized_rerank,
                strict=True,
            )
        ]
        reranked.sort(
            key=lambda item: (-item.final_score, item.document_title.lower(), item.chunk_id)
        )
        return reranked[:top_k]
