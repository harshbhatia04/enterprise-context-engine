"""Optional SQLite persistence for metadata, logs, and eval summaries."""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.schemas import Chunk, Document, EvalSummary
from app.storage.query_log_store import QueryLogEntry, sanitize_query_debug


class SQLiteStore:
    """Small sqlite3-backed persistence layer for optional local state."""

    def __init__(self, db_path: str):
        self.db_path = str(db_path)

    def initialize(self) -> None:
        """Create parent directory and tables when needed."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    document_id TEXT PRIMARY KEY,
                    title TEXT,
                    department TEXT,
                    access_level TEXT,
                    version TEXT,
                    effective_date TEXT,
                    document_type TEXT,
                    source_path TEXT,
                    metadata_json TEXT
                );

                CREATE TABLE IF NOT EXISTS chunks (
                    chunk_id TEXT PRIMARY KEY,
                    document_id TEXT,
                    document_title TEXT,
                    department TEXT,
                    access_level TEXT,
                    document_type TEXT,
                    version TEXT,
                    effective_date TEXT,
                    section_title TEXT,
                    text TEXT,
                    word_count INTEGER,
                    source_path TEXT,
                    metadata_json TEXT
                );

                CREATE TABLE IF NOT EXISTS query_logs (
                    query_id TEXT PRIMARY KEY,
                    user_id TEXT,
                    query TEXT,
                    answer TEXT,
                    safe_abstain INTEGER,
                    citation_count INTEGER,
                    retrieval_mode TEXT,
                    intent TEXT,
                    latency_ms REAL,
                    created_at TEXT,
                    debug_json TEXT
                );

                CREATE TABLE IF NOT EXISTS eval_summaries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT,
                    created_at TEXT,
                    total_examples INTEGER,
                    passed_examples INTEGER,
                    failed_examples INTEGER,
                    metrics_json TEXT,
                    summary_json TEXT
                );
                """
            )

    def clear_all(self) -> None:
        """Clear all persisted tables."""
        self.initialize()
        with self._connect() as conn:
            conn.execute("DELETE FROM documents")
            conn.execute("DELETE FROM chunks")
            conn.execute("DELETE FROM query_logs")
            conn.execute("DELETE FROM eval_summaries")

    def clear_documents_and_chunks(self) -> None:
        """Replace active corpus metadata without deleting logs or eval summaries."""
        self.initialize()
        with self._connect() as conn:
            conn.execute("DELETE FROM documents")
            conn.execute("DELETE FROM chunks")

    def save_documents(self, documents: list[Document]) -> None:
        """Persist document metadata."""
        self.initialize()
        rows = [
            (
                document.document_id,
                document.title,
                document.department,
                document.access_level,
                document.version,
                document.effective_date,
                document.document_type,
                document.source_path,
                to_json(document.metadata),
            )
            for document in documents
        ]
        with self._connect() as conn:
            conn.executemany(
                """
                INSERT OR REPLACE INTO documents (
                    document_id, title, department, access_level, version,
                    effective_date, document_type, source_path, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )

    def load_documents(self) -> list[Document]:
        """Load persisted documents ordered deterministically."""
        self.initialize()
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT document_id, title, department, access_level, version,
                       effective_date, document_type, source_path, metadata_json
                FROM documents
                ORDER BY document_id
                """
            ).fetchall()
        return [
            Document(
                document_id=row["document_id"],
                title=row["title"],
                department=row["department"],
                access_level=row["access_level"],
                version=row["version"],
                effective_date=row["effective_date"],
                document_type=row["document_type"],
                source_path=row["source_path"],
                body="",
                metadata=from_json(row["metadata_json"]) or {},
            )
            for row in rows
        ]

    def save_chunks(self, chunks: list[Chunk]) -> None:
        """Persist chunk metadata and text."""
        self.initialize()
        rows = [
            (
                chunk.chunk_id,
                chunk.document_id,
                chunk.document_title,
                chunk.department,
                chunk.access_level,
                chunk.document_type,
                chunk.version,
                chunk.effective_date,
                chunk.section_title,
                chunk.text,
                chunk.word_count,
                chunk.source_path,
                to_json({}),
            )
            for chunk in chunks
        ]
        with self._connect() as conn:
            conn.executemany(
                """
                INSERT OR REPLACE INTO chunks (
                    chunk_id, document_id, document_title, department, access_level,
                    document_type, version, effective_date, section_title, text,
                    word_count, source_path, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )

    def load_chunks(self) -> list[Chunk]:
        """Load persisted chunks ordered deterministically."""
        self.initialize()
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT chunk_id, document_id, document_title, department, access_level,
                       document_type, version, effective_date, section_title, text,
                       word_count, source_path, metadata_json
                FROM chunks
                ORDER BY chunk_id
                """
            ).fetchall()
        return [
            Chunk(
                chunk_id=row["chunk_id"],
                document_id=row["document_id"],
                document_title=row["document_title"],
                department=row["department"],
                access_level=row["access_level"],
                document_type=row["document_type"],
                version=row["version"],
                effective_date=row["effective_date"],
                section_title=row["section_title"],
                text=row["text"],
                word_count=int(row["word_count"]),
                source_path=row["source_path"],
            )
            for row in rows
        ]

    def add_query_log(self, entry: QueryLogEntry) -> None:
        """Persist a sanitized query log entry."""
        self.initialize()
        debug = sanitize_query_debug(entry.debug)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO query_logs (
                    query_id, user_id, query, answer, safe_abstain, citation_count,
                    retrieval_mode, intent, latency_ms, created_at, debug_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry.query_id,
                    entry.user_id,
                    entry.query,
                    entry.answer,
                    int(entry.safe_abstain),
                    entry.citation_count,
                    entry.retrieval_mode,
                    entry.intent,
                    entry.latency_ms,
                    entry.created_at,
                    to_json(debug),
                ),
            )

    def list_query_logs(self, limit: int = 50) -> list[QueryLogEntry]:
        """Return newest persisted query logs first."""
        self.initialize()
        safe_limit = max(int(limit), 0)
        if safe_limit == 0:
            return []
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT query_id, user_id, query, answer, safe_abstain, citation_count,
                       retrieval_mode, intent, latency_ms, created_at, debug_json
                FROM query_logs
                ORDER BY created_at DESC, query_id DESC
                LIMIT ?
                """,
                (safe_limit,),
            ).fetchall()
        return [
            QueryLogEntry(
                query_id=row["query_id"],
                user_id=row["user_id"],
                query=row["query"],
                answer=row["answer"],
                safe_abstain=bool(row["safe_abstain"]),
                citation_count=int(row["citation_count"]),
                retrieval_mode=row["retrieval_mode"],
                intent=row["intent"],
                latency_ms=row["latency_ms"],
                created_at=row["created_at"],
                debug=from_json(row["debug_json"]) or {},
            )
            for row in rows
        ]

    def clear_query_logs(self) -> None:
        """Clear only query logs."""
        self.initialize()
        with self._connect() as conn:
            conn.execute("DELETE FROM query_logs")

    def next_query_id(self) -> str:
        """Return a deterministic next query id based on persisted logs."""
        self.initialize()
        with self._connect() as conn:
            rows = conn.execute("SELECT query_id FROM query_logs").fetchall()
        max_id = 0
        for row in rows:
            match = re.fullmatch(r"query_(\d{6})", str(row["query_id"]))
            if match:
                max_id = max(max_id, int(match.group(1)))
        return f"query_{max_id + 1:06d}"

    def save_eval_summary(self, source: str, summary: EvalSummary) -> None:
        """Persist the latest deterministic eval summary."""
        self.initialize()
        summary_dict = asdict(summary)
        created_at = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO eval_summaries (
                    source, created_at, total_examples, passed_examples,
                    failed_examples, metrics_json, summary_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    source,
                    created_at,
                    summary.total_examples,
                    summary.passed_examples,
                    summary.failed_examples,
                    to_json(summary.metrics),
                    to_json({"source": source, "created_at": created_at, **summary_dict}),
                ),
            )

    def load_latest_eval_summary(self) -> dict | None:
        """Load latest persisted eval summary payload."""
        self.initialize()
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT source, created_at, total_examples, passed_examples,
                       failed_examples, metrics_json, summary_json
                FROM eval_summaries
                ORDER BY id DESC
                LIMIT 1
                """
            ).fetchone()
        if row is None:
            return None
        summary = from_json(row["summary_json"]) or {}
        return {
            "source": row["source"],
            "created_at": row["created_at"],
            "total_examples": row["total_examples"],
            "passed_examples": row["passed_examples"],
            "failed_examples": row["failed_examples"],
            "metrics": from_json(row["metrics_json"]) or {},
            "summary": summary,
        }

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn


def to_json(data: Any) -> str:
    """Serialize dataclasses, Pydantic models, and plain JSON data."""
    if is_dataclass(data):
        data = asdict(data)
    elif hasattr(data, "model_dump"):
        data = data.model_dump()
    elif hasattr(data, "dict"):
        data = data.dict()
    return json.dumps(data, sort_keys=True)


def from_json(text: str | None) -> Any:
    """Deserialize JSON text with a safe empty fallback."""
    if not text:
        return None
    return json.loads(text)
