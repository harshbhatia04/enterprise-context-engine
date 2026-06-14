"""Run the Milestone 2 sample document ingestion pipeline."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import SAMPLE_DOCS_DIR
from app.ingestion.pipeline import ingest_directory
from app.storage.document_store import InMemoryDocumentStore

def main() -> None:
    documents, chunks = ingest_directory(SAMPLE_DOCS_DIR)
    store = InMemoryDocumentStore()
    store.add_documents(documents)
    store.add_chunks(chunks)

    print(f"Documents ingested: {len(store.list_documents())}")
    print(f"Chunks created: {len(store.list_chunks())}")

    print("\nFirst 3 documents:")
    for document in store.list_documents()[:3]:
        print(f"- {document.document_id} | {document.title} | {document.department}")

    print("\nFirst 3 chunks:")
    for chunk in store.list_chunks()[:3]:
        preview = chunk.text.replace("\n", " ")[:90]
        print(
            f"- {chunk.chunk_id} | section={chunk.section_title} | "
            f"words={chunk.word_count} | {preview}"
        )


if __name__ == "__main__":
    main()
