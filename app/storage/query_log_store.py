"""In-memory query log storage for the API and dashboard."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


FORBIDDEN_DEBUG_KEYS = {
    "context",
    "context_text",
    "chunks",
    "chunk",
    "focused_chunks",
    "candidate_documents",
    "candidate_sections",
    "source_text",
    "raw_context",
}


@dataclass(frozen=True)
class QueryLogEntry:
    query_id: str
    user_id: str
    query: str
    answer: str
    safe_abstain: bool
    citation_count: int
    retrieval_mode: str | None
    intent: str | None
    latency_ms: float | None
    created_at: str
    debug: dict[str, Any] = field(default_factory=dict)


class InMemoryQueryLogStore:
    """Small deterministic in-memory query log store."""

    def __init__(self) -> None:
        self._entries: list[QueryLogEntry] = []
        self._next_id = 1

    def add(self, entry: QueryLogEntry) -> None:
        """Append a prebuilt query log entry."""
        self._entries.append(entry)

    def create_entry(
        self,
        user_id: str,
        query: str,
        answer: str,
        safe_abstain: bool,
        citation_count: int,
        retrieval_mode: str | None,
        intent: str | None,
        latency_ms: float | None,
        debug: dict | None = None,
    ) -> QueryLogEntry:
        """Create and store a sanitized query log entry."""
        entry = QueryLogEntry(
            query_id=f"query_{self._next_id:06d}",
            user_id=user_id,
            query=query,
            answer=answer,
            safe_abstain=safe_abstain,
            citation_count=citation_count,
            retrieval_mode=retrieval_mode,
            intent=intent,
            latency_ms=latency_ms,
            created_at=datetime.now(timezone.utc).isoformat(),
            debug=sanitize_query_debug(debug or {}),
        )
        self._next_id += 1
        self.add(entry)
        return entry

    def list(self, limit: int = 50) -> list[QueryLogEntry]:
        """Return the newest log entries first."""
        safe_limit = max(int(limit), 0)
        if safe_limit == 0:
            return []
        return list(reversed(self._entries[-safe_limit:]))

    def clear(self) -> None:
        """Remove all logs and reset deterministic IDs."""
        self._entries.clear()
        self._next_id = 1


def sanitize_query_debug(debug: dict[str, Any]) -> dict[str, Any]:
    """Remove raw context, chunk, and source-text fields from log debug payloads."""
    sanitized: dict[str, Any] = {}
    for key, value in debug.items():
        normalized_key = str(key).lower()
        if normalized_key in FORBIDDEN_DEBUG_KEYS:
            continue
        if any(token in normalized_key for token in ("context", "chunk", "source_text")):
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            sanitized[key] = value
        elif isinstance(value, list):
            sanitized[key] = [
                item for item in value if isinstance(item, (str, int, float, bool)) or item is None
            ]
        elif isinstance(value, dict):
            nested = sanitize_query_debug(value)
            if nested:
                sanitized[key] = nested
    return sanitized


def _sanitize_debug(debug: dict[str, Any]) -> dict[str, Any]:
    return sanitize_query_debug(debug)
