"""Run a progressive disclosure demo over the sample enterprise documents."""

from __future__ import annotations

import sys
from pathlib import Path
from pprint import pformat

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import SAMPLE_DOCS_DIR
from app.context_engine.progressive_disclosure import ProgressiveDisclosureEngine
from app.ingestion.pipeline import ingest_directory

EXAMPLE_QUERIES = [
    "What is the invoice approval limit?",
    "How do we restore production after a bad release?",
    "Show documents in finance",
    "What section explains data retention?",
    "Compare remote work policy and contractor policy",
    "NDA policy",
    "How do I get paid back for travel costs?",
]


def main() -> int:
    markdown_files = sorted(SAMPLE_DOCS_DIR.glob("*.md"))
    if not markdown_files:
        print("No sample documents found.")
        print("Run: python scripts/create_sample_docs.py")
        return 1

    _, chunks = ingest_directory(SAMPLE_DOCS_DIR)
    engine = ProgressiveDisclosureEngine()

    for query in EXAMPLE_QUERIES:
        result = engine.run(query, chunks=chunks)
        print(f"\nQuery: {query}")
        print(f"Mode: {result.retrieval_plan.retrieval_mode}")

        print("Candidate documents:")
        for rank, document in enumerate(result.candidate_documents, start=1):
            print(
                f"  {rank}. {document.document_title} | "
                f"{document.department} | score={document.score:.3f}"
            )

        print("Candidate sections:")
        for rank, section in enumerate(result.candidate_sections, start=1):
            print(
                f"  {rank}. {section.section_title} | {section.document_title} | "
                f"score={section.score:.3f}"
            )

        print("Focused chunks:")
        for rank, chunk in enumerate(result.focused_chunks, start=1):
            print(
                f"  {rank}. {chunk.document_title} / {chunk.section_title} / "
                f"chunk_id={chunk.chunk_id} / score={chunk.score:.3f}"
            )

        print(f"Debug: {pformat(result.debug)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
