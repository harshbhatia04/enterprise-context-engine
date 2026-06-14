"""Run a small BM25 retrieval smoke test over sample documents."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import SAMPLE_DOCS_DIR
from app.ingestion.pipeline import ingest_directory
from app.retrieval.bm25_retriever import BM25Retriever

EXAMPLE_QUERIES = [
    "invoice approval limit",
    "failed deployment rollback procedure",
    "NDA policy",
    "data retention requirements",
    "database backup schedule",
    "remote work policy",
    "incident response severity",
    "vendor payment approval",
]


def _preview(text: str, limit: int = 120) -> str:
    compact = " ".join(text.split())
    return compact[:limit] + ("..." if len(compact) > limit else "")


def main() -> int:
    markdown_files = sorted(SAMPLE_DOCS_DIR.glob("*.md"))
    if not markdown_files:
        print("No sample documents found.")
        print("Run: python scripts/create_sample_docs.py")
        return 1

    documents, chunks = ingest_directory(SAMPLE_DOCS_DIR)
    retriever = BM25Retriever()
    retriever.build_index(chunks)

    print(f"Indexed {len(chunks)} chunks from {len(documents)} documents.")
    for query in EXAMPLE_QUERIES:
        print(f"\nQuery: {query}\n")
        results = retriever.search(query, top_k=3)
        if not results:
            print("No results.")
            continue
        for rank, result in enumerate(results, start=1):
            print(f"{rank}. {result.document_title}")
            print(f"   Section: {result.section_title}")
            print(f"   Department: {result.department}")
            print(f"   Score: {result.score:.2f}")
            print(f"   Chunk: {result.chunk_id}")
            print(f"   Preview: {_preview(result.text)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
