"""Simple in-memory document store for the MVP."""

from __future__ import annotations

from app.schemas import Chunk, Document


class InMemoryDocumentStore:
    """Store loaded documents and chunks for local demos and tests."""

    def __init__(self) -> None:
        self.documents: dict[str, Document] = {}
        self.chunks: dict[str, Chunk] = {}

    def add_documents(self, documents: list[Document]) -> None:
        for document in documents:
            self.documents[document.document_id] = document

    def add_chunks(self, chunks: list[Chunk]) -> None:
        for chunk in chunks:
            self.chunks[chunk.chunk_id] = chunk

    def list_documents(self) -> list[Document]:
        return list(self.documents.values())

    def list_chunks(self) -> list[Chunk]:
        return list(self.chunks.values())

    def get_chunks_by_document(self, document_id: str) -> list[Chunk]:
        return [chunk for chunk in self.chunks.values() if chunk.document_id == document_id]
