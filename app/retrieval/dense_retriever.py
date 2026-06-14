"""Dense semantic retrieval over ingested chunks."""

from __future__ import annotations

import hashlib
import os
from abc import ABC, abstractmethod

import numpy as np

from app.retrieval.bm25_retriever import tokenize
from app.schemas import Chunk, RetrievalResult


class EmbeddingModel(ABC):
    """Small embedding abstraction used by dense retrieval."""

    @abstractmethod
    def encode(self, texts: list[str]) -> np.ndarray:
        """Return one vector per input text."""


class SentenceTransformerEmbeddingModel(EmbeddingModel):
    """Sentence Transformers embedding model loaded lazily for demos."""

    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        local_files_only: bool = False,
    ) -> None:
        self.model_name = model_name
        self.local_files_only = local_files_only
        self._model = None

    def _load_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            if self.local_files_only:
                os.environ.setdefault("HF_HUB_OFFLINE", "1")
                os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
            try:
                self._model = SentenceTransformer(
                    self.model_name,
                    local_files_only=self.local_files_only,
                )
            except TypeError:
                self._model = SentenceTransformer(self.model_name)
        return self._model

    def encode(self, texts: list[str]) -> np.ndarray:
        model = self._load_model()
        return np.asarray(model.encode(texts, show_progress_bar=False), dtype=float)


class FakeEmbeddingModel(EmbeddingModel):
    """Deterministic local embedding model for tests and offline demos."""

    SYNONYM_GROUPS: dict[str, tuple[str, ...]] = {
        "rollback": ("restore", "revert", "undo", "recover"),
        "deployment": ("release", "production", "deploy", "deployed"),
        "invoice": ("bill", "billing"),
        "reimbursement": ("repay", "repaid", "paid", "back", "travel"),
        "expense": ("expenses", "cost", "costs", "spend", "spending"),
        "remote": ("wfh", "telework"),
        "work": ("home", "guidelines"),
        "retention": ("keep", "store", "preserve", "preserved", "records"),
        "nda": ("confidentiality", "agreement", "non", "disclosure"),
        "incident": ("outage", "failure", "failed"),
    }

    PHRASE_SYNONYMS: dict[str, tuple[str, ...]] = {
        "work from home": ("remote", "work"),
        "paid back": ("reimbursement", "expense"),
        "non disclosure": ("nda",),
        "bad release": ("rollback", "deployment"),
        "restore production": ("rollback", "deployment"),
    }

    def __init__(self, dimensions: int = 384) -> None:
        self.dimensions = dimensions
        self._reverse_synonyms = self._build_reverse_synonyms()

    def encode(self, texts: list[str]) -> np.ndarray:
        vectors = np.vstack([self._encode_one(text) for text in texts]) if texts else np.empty((0, self.dimensions))
        return vectors.astype(float)

    def _encode_one(self, text: str) -> np.ndarray:
        vector = np.zeros(self.dimensions, dtype=float)
        for token in self._expanded_tokens(text):
            index = self._stable_index(token)
            vector[index] += 1.0
        return vector

    def _expanded_tokens(self, text: str) -> list[str]:
        lowered = text.lower()
        expanded: list[str] = []
        for phrase, canonical_tokens in self.PHRASE_SYNONYMS.items():
            if phrase in lowered:
                expanded.extend(canonical_tokens)

        for token in tokenize(text):
            expanded.append(token)
            canonical = self._reverse_synonyms.get(token)
            if canonical is not None:
                expanded.append(canonical)
        return expanded

    def _stable_index(self, token: str) -> int:
        digest = hashlib.md5(token.encode("utf-8"), usedforsecurity=False).hexdigest()
        return int(digest[:8], 16) % self.dimensions

    @classmethod
    def _build_reverse_synonyms(cls) -> dict[str, str]:
        reverse: dict[str, str] = {}
        for canonical, synonyms in cls.SYNONYM_GROUPS.items():
            reverse[canonical] = canonical
            for synonym in synonyms:
                reverse[synonym] = canonical
        return reverse


def normalize_vectors(vectors: np.ndarray) -> np.ndarray:
    """L2-normalize rows while keeping all-zero rows stable."""
    if vectors.size == 0:
        return vectors
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    safe_norms = np.where(norms == 0.0, 1.0, norms)
    return vectors / safe_norms


class DenseRetriever:
    """Dense retriever that ranks chunks by cosine similarity."""

    def __init__(self, embedding_model: EmbeddingModel | None = None) -> None:
        self.embedding_model = embedding_model or SentenceTransformerEmbeddingModel()
        self.chunks: list[Chunk] = []
        self.embeddings: np.ndarray | None = None
        self._index_built = False

    def build_index(self, chunks: list[Chunk]) -> None:
        """Encode chunk text and metadata into a normalized dense index."""
        self.chunks = list(chunks)
        texts = [self._build_searchable_text(chunk) for chunk in self.chunks]
        self.embeddings = normalize_vectors(self.embedding_model.encode(texts))
        self._index_built = True

    def search(self, query: str, top_k: int = 5) -> list[RetrievalResult]:
        """Return the most semantically similar chunks for a query."""
        if not self._index_built:
            raise RuntimeError("Dense index has not been built. Call build_index(chunks) before search().")
        if top_k <= 0 or not self.chunks or self.embeddings is None:
            return []
        if not query.strip():
            return []

        query_embedding = normalize_vectors(self.embedding_model.encode([query]))
        if query_embedding.size == 0:
            return []

        scores = self.embeddings @ query_embedding[0]
        candidates = [
            (float(score), chunk)
            for score, chunk in zip(scores, self.chunks, strict=True)
        ]
        candidates.sort(
            key=lambda item: (-item[0], item[1].document_title.lower(), item[1].chunk_id)
        )
        return [self._to_result(chunk, score) for score, chunk in candidates[:top_k]]

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
    def _to_result(chunk: Chunk, score: float) -> RetrievalResult:
        return RetrievalResult(
            chunk_id=chunk.chunk_id,
            document_id=chunk.document_id,
            document_title=chunk.document_title,
            department=chunk.department,
            access_level=chunk.access_level,
            section_title=chunk.section_title,
            text=chunk.text,
            score=score,
            retrieval_method="dense",
            metadata={
                "document_type": chunk.document_type,
                "version": chunk.version,
                "effective_date": chunk.effective_date,
                "source_path": chunk.source_path,
                "word_count": chunk.word_count,
                "dense_score": score,
            },
            normalized_score=None,
        )


def create_dense_retriever(
    backend: str = "memory",
    embedding_model: EmbeddingModel | None = None,
):
    """Create a dense retriever backend without changing default memory behavior."""
    normalized_backend = backend.strip().lower()
    if normalized_backend == "memory":
        return DenseRetriever(embedding_model)
    if normalized_backend == "qdrant":
        from app.retrieval.qdrant_retriever import QdrantDenseRetriever

        return QdrantDenseRetriever(embedding_model=embedding_model)
    raise ValueError("Dense retriever backend must be 'memory' or 'qdrant'.")
