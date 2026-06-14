"""Vector-store interface for optional dense retrieval backends."""

from __future__ import annotations

from typing import Protocol

import numpy as np

from app.schemas import Chunk, RetrievalResult


class VectorStore(Protocol):
    """Minimal protocol implemented by vector-store backends."""

    def add_chunks(self, chunks: list[Chunk], embeddings: np.ndarray) -> None:
        """Store chunk embeddings and metadata payloads."""

    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 5,
        filters: dict | None = None,
    ) -> list[RetrievalResult]:
        """Return nearest chunks for a query embedding."""

    def clear(self) -> None:
        """Clear indexed vectors."""
