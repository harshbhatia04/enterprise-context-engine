"""Markdown document loading utilities."""

from __future__ import annotations

import re
from pathlib import Path

from app.ingestion.metadata import parse_frontmatter
from app.schemas import Document


def slugify(value: str) -> str:
    """Create a deterministic, readable identifier from a title or filename."""
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "document"


def load_markdown_file(path: Path) -> Document:
    """Load one Markdown file into a normalized Document object."""
    markdown_text = path.read_text(encoding="utf-8")
    metadata, body = parse_frontmatter(markdown_text)

    title = metadata.get("title") or path.stem.replace("-", " ").title()
    department = metadata.get("department", "general")
    access_level = metadata.get("access_level", department or "general")
    version = metadata.get("version", "unknown")
    effective_date = metadata.get("effective_date", "unknown")
    document_type = metadata.get("document_type")

    normalized_metadata = {
        **metadata,
        "title": title,
        "department": department,
        "access_level": access_level,
        "version": version,
        "effective_date": effective_date,
        "document_type": document_type,
    }

    return Document(
        document_id=slugify(title),
        title=title,
        department=department,
        access_level=access_level,
        version=version,
        effective_date=effective_date,
        document_type=document_type,
        source_path=str(path),
        body=body,
        metadata=normalized_metadata,
    )


def load_markdown_directory(directory: Path) -> list[Document]:
    """Load all Markdown files in a directory in deterministic filename order."""
    paths = sorted(path for path in directory.glob("*.md") if path.is_file())
    return [load_markdown_file(path) for path in paths]
