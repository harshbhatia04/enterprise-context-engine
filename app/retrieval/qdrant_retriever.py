"""Optional Qdrant-backed dense retrieval."""

from __future__ import annotations

import os
from typing import Any

import numpy as np

from app.retrieval.dense_retriever import (
    EmbeddingModel,
    FakeEmbeddingModel,
    normalize_vectors,
)
from app.schemas import Chunk, RetrievalResult

try:  # pragma: no cover - exercised only when qdrant-client is installed.
    from qdrant_client import QdrantClient
    from qdrant_client.http import models
except ImportError:  # pragma: no cover - default local environment may omit Qdrant.
    QdrantClient = None
    models = None


QDRANT_AVAILABLE = QdrantClient is not None


class QdrantDenseRetriever:
    """Dense retriever backed by an optional Qdrant collection."""

    def __init__(
        self,
        collection_name: str = "enterprise_context_chunks",
        embedding_model: EmbeddingModel | None = None,
        client: Any | None = None,
        url: str | None = None,
    ) -> None:
        if QdrantClient is None and client is None:
            raise RuntimeError("qdrant-client is not installed. Install qdrant-client to use QdrantDenseRetriever.")
        self.collection_name = (
            os.getenv("QDRANT_COLLECTION", collection_name)
            if collection_name == "enterprise_context_chunks"
            else collection_name
        )
        self.embedding_model = embedding_model or FakeEmbeddingModel()
        self.client = client or self._create_client(url)
        self.point_id_to_chunk_id: dict[int, str] = {}
        self.chunk_id_to_point_id: dict[str, int] = {}
        self._point_payloads: dict[int, dict[str, Any]] = {}
        self._index_built = False
        self._vector_size: int | None = None

    @staticmethod
    def _create_client(url: str | None):
        target = url or os.getenv("QDRANT_URL")
        if not target or target == ":memory:":
            return QdrantClient(":memory:")
        if target.startswith("http://") or target.startswith("https://"):
            return QdrantClient(url=target)
        return QdrantClient(target)

    def build_index(self, chunks: list[Chunk]) -> None:
        """Embed chunks and upsert them into the Qdrant collection."""
        self.clear()
        indexed_chunks = list(chunks)
        if not indexed_chunks:
            self._index_built = True
            return

        texts = [self._build_searchable_text(chunk) for chunk in indexed_chunks]
        embeddings = normalize_vectors(self.embedding_model.encode(texts))
        self._vector_size = int(embeddings.shape[1])
        self._create_collection(self._vector_size)

        points = []
        for point_id, (chunk, embedding) in enumerate(zip(indexed_chunks, embeddings, strict=True), start=1):
            payload = self._payload_from_chunk(chunk)
            self.point_id_to_chunk_id[point_id] = chunk.chunk_id
            self.chunk_id_to_point_id[chunk.chunk_id] = point_id
            self._point_payloads[point_id] = payload
            points.append(
                models.PointStruct(
                    id=point_id,
                    vector=embedding.tolist(),
                    payload=payload,
                )
            )

        self.client.upsert(collection_name=self.collection_name, points=points)
        self._index_built = True

    def search(
        self,
        query: str,
        top_k: int = 5,
        filters: dict | None = None,
    ) -> list[RetrievalResult]:
        """Return Qdrant semantic search results for a query."""
        if not self._index_built:
            raise RuntimeError("Qdrant dense index has not been built. Call build_index(chunks) before search().")
        if top_k <= 0 or not query.strip():
            return []

        query_embedding = normalize_vectors(self.embedding_model.encode([query]))
        if query_embedding.size == 0:
            return []

        candidate_k = max(top_k * 5, 20) if filters else top_k
        raw_results = self._query(query_embedding[0], candidate_k)
        results = [self._to_result(point) for point in raw_results]
        if filters:
            results = [result for result in results if self._matches_filters(result.metadata, filters)]
        results.sort(key=lambda result: (-result.score, result.document_title.lower(), result.chunk_id))
        return results[:top_k]

    def clear(self) -> None:
        """Delete the collection and local ID mappings if it exists."""
        self.point_id_to_chunk_id.clear()
        self.chunk_id_to_point_id.clear()
        self._point_payloads.clear()
        self._index_built = False
        self._vector_size = None
        try:
            if self._collection_exists():
                self.client.delete_collection(self.collection_name)
        except Exception:
            return

    def _create_collection(self, vector_size: int) -> None:
        if models is None:
            raise RuntimeError("qdrant-client models are unavailable.")
        if self._collection_exists():
            self.client.delete_collection(self.collection_name)
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=models.VectorParams(size=vector_size, distance=models.Distance.COSINE),
        )

    def _collection_exists(self) -> bool:
        if hasattr(self.client, "collection_exists"):
            return bool(self.client.collection_exists(self.collection_name))
        try:
            self.client.get_collection(self.collection_name)
            return True
        except Exception:
            return False

    def _query(self, query_embedding: np.ndarray, limit: int) -> list[Any]:
        query_vector = query_embedding.tolist()
        if hasattr(self.client, "query_points"):
            response = self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                limit=limit,
                with_payload=True,
            )
            return list(getattr(response, "points", response))
        return list(
            self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=limit,
                with_payload=True,
            )
        )

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
    def _payload_from_chunk(chunk: Chunk) -> dict[str, Any]:
        return {
            "chunk_id": chunk.chunk_id,
            "document_id": chunk.document_id,
            "document_title": chunk.document_title,
            "department": chunk.department,
            "access_level": chunk.access_level,
            "section_title": chunk.section_title,
            "text": chunk.text,
            "version": chunk.version,
            "effective_date": chunk.effective_date,
            "document_type": chunk.document_type,
            "source_path": chunk.source_path,
            "metadata": {
                "document_type": chunk.document_type,
                "version": chunk.version,
                "effective_date": chunk.effective_date,
                "source_path": chunk.source_path,
                "word_count": chunk.word_count,
            },
        }

    def _to_result(self, point: Any) -> RetrievalResult:
        payload = dict(getattr(point, "payload", None) or {})
        score = float(getattr(point, "score", 0.0) or 0.0)
        metadata = {
            **dict(payload.get("metadata") or {}),
            "qdrant_score": score,
            "point_id": getattr(point, "id", None),
        }
        return RetrievalResult(
            chunk_id=str(payload.get("chunk_id", "")),
            document_id=str(payload.get("document_id", "")),
            document_title=str(payload.get("document_title", "")),
            department=str(payload.get("department", "")),
            access_level=str(payload.get("access_level", "")),
            section_title=str(payload.get("section_title", "")),
            text=str(payload.get("text", "")),
            score=score,
            retrieval_method="qdrant_dense",
            metadata={**payload, **metadata},
            normalized_score=None,
        )

    @staticmethod
    def _matches_filters(metadata: dict[str, Any], filters: dict) -> bool:
        for key, expected in filters.items():
            if metadata.get(key) != expected:
                return False
        return True
