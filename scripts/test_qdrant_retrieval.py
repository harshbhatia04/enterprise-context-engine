"""Run an optional Qdrant dense retrieval demo over sample documents."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import SAMPLE_DOCS_DIR
from app.ingestion.pipeline import ingest_directory
from app.retrieval.dense_retriever import FakeEmbeddingModel
from app.retrieval.qdrant_retriever import QDRANT_AVAILABLE, QdrantDenseRetriever
from scripts.create_sample_docs import create_sample_docs


QUERIES = [
    "how do we restore production after a bad release",
    "how do I get paid back for travel costs",
    "confidentiality agreement rules",
]


def _preview(text: str, limit: int = 90) -> str:
    compact = " ".join(text.split())
    return compact[:limit] + ("..." if len(compact) > limit else "")


def _print_results(query: str, results) -> None:
    print(f"\nQuery: {query}")
    if not results:
        print("  No results")
        return
    for index, result in enumerate(results, start=1):
        print(f"  {index}. {result.document_title} / {result.section_title}")
        print(f"     Department: {result.department}")
        print(f"     Score: {result.score:.3f}")
        print(f"     Method: {result.retrieval_method}")
        print(f"     Chunk: {result.chunk_id}")
        print(f"     Preview: {_preview(result.text)}")


def main() -> int:
    if not QDRANT_AVAILABLE:
        print("qdrant-client is not installed; skipping optional Qdrant demo.")
        print("Install qdrant-client to run this demo, or keep using the default memory backend.")
        return 0

    if not sorted(SAMPLE_DOCS_DIR.glob("*.md")):
        create_sample_docs(SAMPLE_DOCS_DIR)

    _, chunks = ingest_directory(SAMPLE_DOCS_DIR)
    try:
        retriever = QdrantDenseRetriever(
            embedding_model=FakeEmbeddingModel(),
            url=":memory:",
        )
        retriever.build_index(chunks)
    except Exception as exc:
        print("Could not start the optional in-memory Qdrant demo.")
        print(f"Reason: {exc}")
        return 0

    print(f"Indexed {len(chunks)} chunks into in-memory Qdrant collection '{retriever.collection_name}'.")
    for query in QUERIES:
        _print_results(query, retriever.search(query, top_k=3))
    retriever.clear()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
