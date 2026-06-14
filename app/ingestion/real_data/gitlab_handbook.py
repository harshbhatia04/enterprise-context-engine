"""Local GitLab Handbook-style public documentation ingestion."""

from __future__ import annotations

from pathlib import Path

from app.ingestion.chunker import chunk_document
from app.ingestion.loaders import slugify
from app.ingestion.metadata import parse_frontmatter
from app.schemas import Chunk, Document

SOURCE_NAME = "gitlab_handbook"
DEFAULT_SOURCE_URL = "https://handbook.gitlab.com/"

DEPARTMENT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "hr": (
        "people",
        "benefits",
        "hiring",
        "onboarding",
        "team member",
        "remote work",
        "communication",
    ),
    "engineering": (
        "engineering",
        "development",
        "infrastructure",
        "incident",
        "security operations",
        "production",
    ),
    "finance": (
        "finance",
        "expense",
        "expenses",
        "procurement",
        "travel",
        "accounting",
    ),
    "legal": (
        "legal",
        "privacy",
        "compliance",
        "contract",
        "security",
        "data protection",
    ),
}


def infer_gitlab_department(path: str, title: str, body: str) -> str:
    """Infer a department from a GitLab Handbook path, title, and body."""
    haystack = " ".join([path, title, body]).lower()
    scores = {
        department: sum(1 for keyword in keywords if keyword in haystack)
        for department, keywords in DEPARTMENT_KEYWORDS.items()
    }
    best_score = max(scores.values(), default=0)
    if best_score == 0:
        return "general"
    winners = [department for department, score in scores.items() if score == best_score]
    return winners[0] if len(winners) == 1 else "general"


def normalize_gitlab_metadata(metadata: dict, source_path: str, body: str) -> dict:
    """Normalize metadata for public GitLab Handbook-style documents."""
    path = Path(source_path)
    title = str(metadata.get("title") or path.stem.replace("-", " ").title()).strip()
    department = str(metadata.get("department") or "").strip().lower()
    if not department or department == "general":
        department = infer_gitlab_department(source_path, title, body)

    return {
        **metadata,
        "title": title,
        "department": department,
        "access_level": "public",
        "version": str(metadata.get("version") or "public"),
        "effective_date": str(metadata.get("effective_date") or "unknown"),
        "document_type": "handbook",
        "source_path": source_path,
        "source_name": SOURCE_NAME,
        "source_url": str(metadata.get("source_url") or DEFAULT_SOURCE_URL),
    }


def load_gitlab_handbook_directory(directory: Path) -> list[Document]:
    """Load local GitLab Handbook-style Markdown files as Documents."""
    paths = sorted(
        path
        for path in directory.glob("*.md")
        if path.is_file() and path.name.lower() != "readme.md"
    )
    documents: list[Document] = []
    for path in paths:
        markdown_text = path.read_text(encoding="utf-8")
        metadata, body = parse_frontmatter(markdown_text)
        normalized = normalize_gitlab_metadata(metadata, str(path), body)
        title = normalized["title"]
        documents.append(
            Document(
                document_id=f"gitlab-{slugify(title)}",
                title=title,
                department=normalized["department"],
                access_level=normalized["access_level"],
                version=normalized["version"],
                effective_date=normalized["effective_date"],
                document_type=normalized["document_type"],
                source_path=str(path),
                body=body,
                metadata=normalized,
            )
        )
    return documents


def ingest_gitlab_handbook_directory(directory: Path) -> tuple[list[Document], list[Chunk]]:
    """Load and chunk local GitLab Handbook-style Markdown documents."""
    documents = load_gitlab_handbook_directory(directory)
    chunks: list[Chunk] = []
    for document in documents:
        chunks.extend(chunk_document(document, target_words=350, overlap_words=50))
    return documents, chunks
