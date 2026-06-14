"""Section-aware Markdown chunking."""

from __future__ import annotations

import re
from dataclasses import replace

from app.schemas import Chunk, Document

HEADING_RE = re.compile(r"^(#{1,3})\s+(.+?)\s*#*\s*$")


def _normalize_text(text: str) -> str:
    lines = [line.rstrip() for line in text.strip().splitlines()]
    return "\n".join(lines).strip()


def _word_count(text: str) -> int:
    return len(text.split())


def _extract_heading_title(line: str) -> str | None:
    match = HEADING_RE.match(line.strip())
    if not match:
        return None
    return match.group(2).strip() or None


def _extract_sections(body: str) -> list[tuple[str, str]]:
    """Split Markdown body into heading-scoped sections."""
    lines = body.splitlines()
    sections: list[tuple[str, list[str]]] = []
    current_title = "Document Body"
    current_lines: list[str] = []
    saw_heading = False

    for line in lines:
        heading_title = _extract_heading_title(line)
        if heading_title is not None:
            if current_lines:
                sections.append((current_title, current_lines))
            current_title = heading_title
            current_lines = [line]
            saw_heading = True
            continue
        current_lines.append(line)

    if current_lines:
        sections.append((current_title, current_lines))

    if not saw_heading:
        normalized_body = _normalize_text(body)
        return [("Document Body", normalized_body)] if normalized_body else []

    normalized_sections: list[tuple[str, str]] = []
    for section_title, section_lines in sections:
        if _is_heading_only_section(section_lines):
            continue
        text = _normalize_text("\n".join(section_lines))
        if text:
            normalized_sections.append((section_title, text))
    return normalized_sections


def _is_heading_only_section(lines: list[str]) -> bool:
    if not lines or _extract_heading_title(lines[0]) is None:
        return False
    return not any(line.strip() for line in lines[1:])


def _split_long_text(text: str, target_words: int, overlap_words: int) -> list[str]:
    words = text.split()
    if not words:
        return []
    if len(words) <= target_words:
        return [text]

    step = target_words - overlap_words
    if step <= 0:
        step = target_words

    windows: list[str] = []
    for start in range(0, len(words), step):
        window_words = words[start : start + target_words]
        if window_words:
            windows.append(" ".join(window_words))
        if start + target_words >= len(words):
            break
    return windows


def _build_chunk(document: Document, section_title: str, text: str, index: int) -> Chunk:
    cleaned_text = _normalize_text(text)
    return Chunk(
        chunk_id=f"{document.document_id}::chunk_{index:04d}",
        document_id=document.document_id,
        document_title=document.title,
        department=document.department,
        access_level=document.access_level,
        document_type=document.document_type,
        version=document.version,
        effective_date=document.effective_date,
        section_title=section_title,
        text=cleaned_text,
        word_count=_word_count(cleaned_text),
        source_path=document.source_path,
    )


def chunk_document(
    document: Document,
    target_words: int = 350,
    overlap_words: int = 50,
) -> list[Chunk]:
    """Split a document into deterministic section-aware chunks."""
    if target_words <= 0:
        raise ValueError("target_words must be greater than zero")
    if overlap_words < 0:
        raise ValueError("overlap_words must be zero or greater")

    # Defensively normalize accidental frontmatter if a caller bypasses loaders.
    body = document.body
    if body.lstrip().startswith("---"):
        from app.ingestion.metadata import parse_frontmatter

        _, body = parse_frontmatter(body)
        document = replace(document, body=body)

    chunks: list[Chunk] = []
    for section_title, section_text in _extract_sections(document.body):
        for window_text in _split_long_text(section_text, target_words, overlap_words):
            cleaned_text = _normalize_text(window_text)
            if not cleaned_text:
                continue
            chunks.append(_build_chunk(document, section_title, cleaned_text, len(chunks)))

    return chunks
