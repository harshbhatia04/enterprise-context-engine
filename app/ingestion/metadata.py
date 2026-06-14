"""Frontmatter parsing helpers for Markdown ingestion."""

from __future__ import annotations


def _clean_metadata_value(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1].strip()
    return value


def parse_frontmatter(markdown_text: str) -> tuple[dict[str, str], str]:
    """Parse simple YAML-style frontmatter from Markdown text.

    The MVP only needs deterministic string metadata, so this intentionally
    avoids a full YAML dependency. Malformed frontmatter is treated as plain
    document body instead of raising.
    """
    text = markdown_text.lstrip("\ufeff")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text.strip()

    closing_index: int | None = None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            closing_index = index
            break

    if closing_index is None:
        return {}, text.strip()

    metadata: dict[str, str] = {}
    for line in lines[1:closing_index]:
        if not line.strip() or line.lstrip().startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        if key:
            metadata[key] = _clean_metadata_value(value)

    body = "\n".join(lines[closing_index + 1 :]).strip()
    return metadata, body
