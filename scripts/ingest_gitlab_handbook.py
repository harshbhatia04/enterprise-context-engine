"""Ingest local GitLab Handbook-style Markdown files."""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ingestion.real_data.gitlab_handbook import ingest_gitlab_handbook_directory

GITLAB_SOURCE_DIR = PROJECT_ROOT / "data" / "real_sources" / "gitlab_handbook"


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest GitLab Handbook-style local Markdown files.")
    parser.add_argument("--local", action="store_true", help="Use local Markdown files. This is the default.")
    parser.add_argument(
        "--download",
        action="store_true",
        help="Reserved for a future explicit live download mode. Not implemented in this MVP.",
    )
    args = parser.parse_args()

    if args.download:
        print("Live download is not implemented in this MVP.")
        print("Use: python scripts/create_gitlab_fixture_docs.py")
        print("Then: python scripts/ingest_gitlab_handbook.py --local")
        return 2

    markdown_files = [
        path
        for path in sorted(GITLAB_SOURCE_DIR.glob("*.md"))
        if path.name.lower() != "readme.md"
    ]
    if not markdown_files:
        print("No GitLab Handbook-style Markdown files found.")
        print("Run: python scripts/create_gitlab_fixture_docs.py")
        return 1

    documents, chunks = ingest_gitlab_handbook_directory(GITLAB_SOURCE_DIR)
    departments = Counter(document.department for document in documents)

    print("GitLab Handbook Ingestion")
    print(f"Documents loaded: {len(documents)}")
    print(f"Chunks created: {len(chunks)}")
    print("Department distribution:")
    for department, count in sorted(departments.items()):
        print(f"- {department}: {count}")

    print("\nFirst documents:")
    for document in documents[:5]:
        print(f"- {document.document_id} | {document.title} | {document.department} | {document.access_level}")

    print("\nExample chunks:")
    for chunk in chunks[:3]:
        preview = " ".join(chunk.text.split())[:100]
        print(
            f"- {chunk.chunk_id} | {chunk.document_title} | "
            f"section={chunk.section_title} | words={chunk.word_count} | {preview}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
