"""First-class BM25 keyword retrieval over ingested chunks."""

from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Sequence

from app.schemas import Chunk, RetrievalResult

try:
    from rank_bm25 import BM25Okapi
except ImportError:  # pragma: no cover - exercised only when dependency is absent.
    BM25Okapi = None

TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    """Tokenize text with deterministic lowercase alphanumeric terms."""
    return TOKEN_RE.findall(text.lower())


class _SimpleBM25:
    """Small BM25 fallback used when rank-bm25 is not installed."""

    def __init__(self, corpus: Sequence[Sequence[str]], k1: float = 1.5, b: float = 0.75) -> None:
        self.corpus = [list(document) for document in corpus]
        self.k1 = k1
        self.b = b
        self.doc_count = len(self.corpus)
        self.doc_lengths = [len(document) for document in self.corpus]
        self.average_doc_length = (
            sum(self.doc_lengths) / self.doc_count if self.doc_count else 0.0
        )
        self.term_frequencies = [Counter(document) for document in self.corpus]
        document_frequencies: Counter[str] = Counter()
        for document in self.corpus:
            document_frequencies.update(set(document))
        self.idf = {
            term: math.log(1 + (self.doc_count - frequency + 0.5) / (frequency + 0.5))
            for term, frequency in document_frequencies.items()
        }

    def get_scores(self, query_tokens: Sequence[str]) -> list[float]:
        if not self.corpus or not query_tokens:
            return [0.0 for _ in self.corpus]

        scores: list[float] = []
        for index, frequencies in enumerate(self.term_frequencies):
            score = 0.0
            document_length = self.doc_lengths[index] or 1
            for term in query_tokens:
                term_frequency = frequencies.get(term, 0)
                if term_frequency == 0:
                    continue
                idf = self.idf.get(term, 0.0)
                denominator = term_frequency + self.k1 * (
                    1 - self.b + self.b * document_length / (self.average_doc_length or 1)
                )
                score += idf * (term_frequency * (self.k1 + 1)) / denominator
            scores.append(score)
        return scores


class BM25Retriever:
    """Keyword retriever that indexes chunk text and useful metadata."""

    def __init__(self) -> None:
        self.chunks: list[Chunk] = []
        self.tokenized_corpus: list[list[str]] = []
        self._bm25: object | None = None
        self._index_built = False

    def build_index(self, chunks: list[Chunk]) -> None:
        """Build a BM25 index from ingested chunks."""
        self.chunks = list(chunks)
        self.tokenized_corpus = [
            tokenize(self._build_searchable_text(chunk)) for chunk in self.chunks
        ]
        if self.chunks:
            bm25_class = BM25Okapi or _SimpleBM25
            self._bm25 = bm25_class(self.tokenized_corpus)
        else:
            self._bm25 = None
        self._index_built = True

    def search(self, query: str, top_k: int = 5) -> list[RetrievalResult]:
        """Return the highest-scoring BM25 results for a query."""
        if not self._index_built:
            raise RuntimeError("BM25 index has not been built. Call build_index(chunks) before search().")
        if top_k <= 0 or not self.chunks:
            return []

        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        if self._bm25 is None:
            return []

        raw_scores = self._bm25.get_scores(query_tokens)
        scores = [float(score) for score in raw_scores]
        all_scores_zero = all(score <= 0.0 for score in scores)

        candidates: list[tuple[float, float, float, Chunk]] = []
        for chunk, score in zip(self.chunks, scores, strict=True):
            if score > 0.0 or all_scores_zero:
                boost = self._metadata_match_boost(chunk, query_tokens)
                candidates.append((score + boost, score, boost, chunk))

        candidates.sort(
            key=lambda item: (-item[0], item[3].document_title.lower(), item[3].chunk_id)
        )
        return [
            self._to_result(chunk, adjusted_score, bm25_score, boost)
            for adjusted_score, bm25_score, boost, chunk in candidates[:top_k]
        ]

    @staticmethod
    def _build_searchable_text(chunk: Chunk) -> str:
        return " ".join(
            [
                chunk.document_title,
                chunk.department,
                chunk.section_title,
                chunk.text,
            ]
        )

    @staticmethod
    def _metadata_match_boost(chunk: Chunk, query_tokens: list[str]) -> float:
        query_token_set = set(query_tokens)
        title_matches = query_token_set.intersection(tokenize(chunk.document_title))
        section_matches = query_token_set.intersection(tokenize(chunk.section_title))
        return (1.5 * len(title_matches)) + (1.0 * len(section_matches))

    @staticmethod
    def _to_result(
        chunk: Chunk,
        score: float,
        bm25_score: float,
        metadata_boost: float,
    ) -> RetrievalResult:
        return RetrievalResult(
            chunk_id=chunk.chunk_id,
            document_id=chunk.document_id,
            document_title=chunk.document_title,
            department=chunk.department,
            access_level=chunk.access_level,
            section_title=chunk.section_title,
            text=chunk.text,
            score=score,
            retrieval_method="bm25",
            metadata={
                "document_type": chunk.document_type,
                "version": chunk.version,
                "effective_date": chunk.effective_date,
                "source_path": chunk.source_path,
                "word_count": chunk.word_count,
                "bm25_score": bm25_score,
                "metadata_match_boost": metadata_boost,
            },
        )
