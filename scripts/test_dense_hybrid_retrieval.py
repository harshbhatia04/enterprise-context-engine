"""Compare BM25, dense, and hybrid retrieval over sample documents."""

from __future__ import annotations

import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import SAMPLE_DOCS_DIR
from app.ingestion.pipeline import ingest_directory
from app.retrieval.bm25_retriever import BM25Retriever
from app.retrieval.dense_retriever import (
    DenseRetriever,
    FakeEmbeddingModel,
    SentenceTransformerEmbeddingModel,
)
from app.retrieval.hybrid_retriever import HybridRetriever

EXAMPLE_QUERIES = [
    "invoice approval limit",
    "billing approval rules",
    "failed deployment rollback procedure",
    "how do we restore production after a bad release",
    "NDA policy",
    "confidentiality agreement rules",
    "remote work policy",
    "work from home guidelines",
    "data retention requirements",
    "how long should records be preserved",
]


def _preview(text: str, limit: int = 90) -> str:
    compact = " ".join(text.split())
    return compact[:limit] + ("..." if len(compact) > limit else "")


def _print_top(label: str, results) -> None:
    if not results:
        print(f"{label} top result: no results")
        return
    result = results[0]
    print(f"{label} top result:")
    print(f"  Document: {result.document_title}")
    print(f"  Section: {result.section_title}")
    print(f"  Department: {result.department}")
    print(f"  Score: {result.score:.3f}")
    print(f"  Chunk: {result.chunk_id}")
    print(f"  Preview: {_preview(result.text)}")


def _build_dense_retriever(chunks) -> DenseRetriever:
    if os.getenv("ECE_USE_REAL_EMBEDDINGS") != "1":
        print("Dense embeddings: FakeEmbeddingModel (set ECE_USE_REAL_EMBEDDINGS=1 to try sentence-transformers)")
        dense = DenseRetriever(FakeEmbeddingModel())
        dense.build_index(chunks)
        return dense

    try:
        dense = DenseRetriever(SentenceTransformerEmbeddingModel(local_files_only=True))
        dense.build_index(chunks)
        print("Dense embeddings: sentence-transformers/all-MiniLM-L6-v2")
        return dense
    except Exception as exc:
        print("Could not load SentenceTransformer model; falling back to FakeEmbeddingModel.")
        print(f"Reason: {exc}")
        dense = DenseRetriever(FakeEmbeddingModel())
        dense.build_index(chunks)
        return dense


def main() -> int:
    markdown_files = sorted(SAMPLE_DOCS_DIR.glob("*.md"))
    if not markdown_files:
        print("No sample documents found.")
        print("Run: python scripts/create_sample_docs.py")
        return 1

    documents, chunks = ingest_directory(SAMPLE_DOCS_DIR)
    bm25 = BM25Retriever()
    bm25.build_index(chunks)
    dense = _build_dense_retriever(chunks)
    hybrid = HybridRetriever(bm25, dense, alpha=0.65)

    print(f"Indexed {len(chunks)} chunks from {len(documents)} documents.")
    for query in EXAMPLE_QUERIES:
        print(f"\nQuery: {query}\n")
        _print_top("BM25", bm25.search(query, top_k=3))
        _print_top("Dense", dense.search(query, top_k=3))
        _print_top("Hybrid", hybrid.search(query, top_k=3, candidate_k=20))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
