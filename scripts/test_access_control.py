"""Run permission-aware progressive disclosure scenarios."""

from __future__ import annotations

import sys
from pathlib import Path
from pprint import pformat

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import SAMPLE_DOCS_DIR
from app.context_engine.progressive_disclosure import SecureProgressiveDisclosureEngine
from app.ingestion.pipeline import ingest_directory

SCENARIOS = [
    ("finance_user", "What is the invoice approval limit?"),
    ("intern_user", "What is the invoice approval limit?"),
    ("engineer_user", "How do we restore production after a bad release?"),
    ("hr_user", "How do we restore production after a bad release?"),
    ("admin_user", "NDA policy"),
    ("intern_user", "NDA policy"),
]


def main() -> int:
    markdown_files = sorted(SAMPLE_DOCS_DIR.glob("*.md"))
    if not markdown_files:
        print("No sample documents found.")
        print("Run: python scripts/create_sample_docs.py")
        return 1

    _, chunks = ingest_directory(SAMPLE_DOCS_DIR)
    engine = SecureProgressiveDisclosureEngine()

    for user_id, query in SCENARIOS:
        result = engine.run(query, user_id=user_id, chunks=chunks)
        print(f"\nUser: {user_id}")
        print(f"Query: {query}")
        print(f"Safe abstain: {result.safe_abstain}")
        if result.safe_message:
            print(f"Safe message: {result.safe_message}")

        print("Accessible candidate documents:")
        for rank, document in enumerate(result.candidate_documents, start=1):
            print(f"  {rank}. {document.document_title} | {document.department}")
        if not result.candidate_documents:
            print("  none")

        print("Accessible focused chunks:")
        for rank, chunk in enumerate(result.focused_chunks, start=1):
            print(
                f"  {rank}. {chunk.document_title} / {chunk.section_title} / "
                f"{chunk.chunk_id}"
            )
        if not result.focused_chunks:
            print("  none")

        print(f"Debug: {pformat(result.debug)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
