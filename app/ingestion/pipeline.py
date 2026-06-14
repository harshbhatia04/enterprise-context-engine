"""Document ingestion pipeline."""

from __future__ import annotations

from pathlib import Path

from app.ingestion.chunker import chunk_document
from app.ingestion.loaders import load_markdown_directory
from app.schemas import Chunk, Document


def ingest_directory(
    directory: Path,
    target_words: int = 350,
    overlap_words: int = 50,
) -> tuple[list[Document], list[Chunk]]:
    """Load Markdown documents from a directory and return their chunks."""
    documents = load_markdown_directory(directory)
    chunks: list[Chunk] = []
    for document in documents:
        chunks.extend(
            chunk_document(
                document,
                target_words=target_words,
                overlap_words=overlap_words,
            )
        )
    return documents, chunks
