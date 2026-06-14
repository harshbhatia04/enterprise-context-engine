"""Run secure reranking and context-building scenarios."""

from __future__ import annotations

import sys
from pathlib import Path
from pprint import pformat

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import SAMPLE_DOCS_DIR
from app.context_engine.context_builder import build_secure_context
from app.ingestion.pipeline import ingest_directory

SCENARIOS = [
    ("finance_user", "What is the invoice approval limit?"),
    ("intern_user", "What is the invoice approval limit?"),
    ("engineer_user", "How do we restore production after a bad release?"),
    ("hr_user", "How do we restore production after a bad release?"),
    ("admin_user", "NDA policy"),
]


def main() -> int:
    markdown_files = sorted(SAMPLE_DOCS_DIR.glob("*.md"))
    if not markdown_files:
        print("No sample documents found.")
        print("Run: python scripts/create_sample_docs.py")
        return 1

    _, chunks = ingest_directory(SAMPLE_DOCS_DIR)
    for user_id, query in SCENARIOS:
        result = build_secure_context(query, user_id, chunks, top_k=5)
        print(f"\nUser: {user_id}")
        print(f"Query: {query}")
        print(f"Safe abstain: {result.safe_abstain}")
        if result.safe_message:
            print(f"Safe message: {result.safe_message}")
        print("Context:")
        print(result.context_text or "  <empty>")
        print("Citations:")
        for citation in result.citations:
            print(
                f"  [{citation.source_id}] {citation.document_title} / "
                f"{citation.section_title} / {citation.department}"
            )
        if not result.citations:
            print("  none")
        print(f"Debug: {pformat(result.debug)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
