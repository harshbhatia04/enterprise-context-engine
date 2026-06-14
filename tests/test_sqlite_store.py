from pathlib import Path

from app.schemas import Chunk, Document, EvalSummary
from app.storage.query_log_store import QueryLogEntry
from app.storage.sqlite_store import SQLiteStore


def make_store(tmp_path: Path) -> SQLiteStore:
    return SQLiteStore(str(tmp_path / "state.db"))


def make_document() -> Document:
    return Document(
        document_id="doc-1",
        title="Remote Work Policy",
        department="hr",
        access_level="hr",
        version="1.0",
        effective_date="2026-01-01",
        document_type="policy",
        source_path="remote.md",
        body="Raw body is not persisted in document metadata rows.",
        metadata={"source_name": "sample", "nested": {"team": "hr"}},
    )


def make_chunk() -> Chunk:
    return Chunk(
        chunk_id="doc-1::chunk_0001",
        document_id="doc-1",
        document_title="Remote Work Policy",
        department="hr",
        access_level="hr",
        document_type="policy",
        version="1.0",
        effective_date="2026-01-01",
        section_title="Eligibility",
        text="Remote work eligibility guidance.",
        word_count=4,
        source_path="remote.md",
    )


def make_log(debug: dict | None = None) -> QueryLogEntry:
    return QueryLogEntry(
        query_id="query_000001",
        user_id="hr_user",
        query="remote work",
        answer="Grounded answer [1]",
        safe_abstain=False,
        citation_count=1,
        retrieval_mode="hybrid",
        intent="policy_lookup",
        latency_ms=12.5,
        created_at="2026-06-12T00:00:00+00:00",
        debug=debug or {"retrieval_mode": "hybrid"},
    )


def make_summary() -> EvalSummary:
    return EvalSummary(
        total_examples=1,
        passed_examples=1,
        failed_examples=0,
        metrics={"pass_rate": 1.0},
        results=[],
    )


def test_initialize_creates_database_tables(tmp_path: Path) -> None:
    store = make_store(tmp_path)

    store.initialize()

    assert Path(store.db_path).exists()


def test_save_load_documents_roundtrip_preserves_metadata(tmp_path: Path) -> None:
    store = make_store(tmp_path)

    store.save_documents([make_document()])
    documents = store.load_documents()

    assert len(documents) == 1
    assert documents[0].title == "Remote Work Policy"
    assert documents[0].metadata["nested"]["team"] == "hr"


def test_save_load_chunks_roundtrip(tmp_path: Path) -> None:
    store = make_store(tmp_path)

    store.save_chunks([make_chunk()])
    chunks = store.load_chunks()

    assert len(chunks) == 1
    assert chunks[0].chunk_id == "doc-1::chunk_0001"
    assert chunks[0].text == "Remote work eligibility guidance."


def test_query_log_add_list_roundtrip(tmp_path: Path) -> None:
    store = make_store(tmp_path)

    store.add_query_log(make_log())
    logs = store.list_query_logs()

    assert len(logs) == 1
    assert logs[0].query_id == "query_000001"
    assert logs[0].citation_count == 1


def test_clear_query_logs_works(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    store.add_query_log(make_log())

    store.clear_query_logs()

    assert store.list_query_logs() == []


def test_save_load_eval_summary(tmp_path: Path) -> None:
    store = make_store(tmp_path)

    store.save_eval_summary("sample_docs", make_summary())
    latest = store.load_latest_eval_summary()

    assert latest is not None
    assert latest["source"] == "sample_docs"
    assert latest["metrics"]["pass_rate"] == 1.0


def test_clear_all_clears_data(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    store.save_documents([make_document()])
    store.save_chunks([make_chunk()])
    store.add_query_log(make_log())
    store.save_eval_summary("sample_docs", make_summary())

    store.clear_all()

    assert store.load_documents() == []
    assert store.load_chunks() == []
    assert store.list_query_logs() == []
    assert store.load_latest_eval_summary() is None


def test_raw_context_key_is_not_stored_in_query_log_debug(tmp_path: Path) -> None:
    store = make_store(tmp_path)

    store.add_query_log(
        make_log(
            {
                "retrieval_mode": "hybrid",
                "context_text": "restricted raw context",
                "included_chunks": ["raw chunk"],
            }
        )
    )

    debug = store.list_query_logs()[0].debug
    assert "retrieval_mode" in debug
    assert "context_text" not in debug
    assert "included_chunks" not in debug
