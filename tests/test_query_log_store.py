from app.storage.query_log_store import InMemoryQueryLogStore


def test_query_log_ids_increment_deterministically() -> None:
    store = InMemoryQueryLogStore()

    first = store.create_entry("finance_user", "q1", "a1", False, 1, "hybrid", "exact_lookup", 1.0)
    second = store.create_entry("intern_user", "q2", "a2", True, 0, "hybrid", "exact_lookup", 2.0)

    assert first.query_id == "query_000001"
    assert second.query_id == "query_000002"


def test_query_log_list_limit_returns_newest_first() -> None:
    store = InMemoryQueryLogStore()
    for index in range(3):
        store.create_entry("user", f"q{index}", "answer", False, 1, "hybrid", "intent", 1.0)

    logs = store.list(limit=2)

    assert [entry.query_id for entry in logs] == ["query_000003", "query_000002"]


def test_query_log_clear_resets_entries_and_ids() -> None:
    store = InMemoryQueryLogStore()
    store.create_entry("user", "q", "a", False, 1, "hybrid", "intent", 1.0)

    store.clear()
    next_entry = store.create_entry("user", "q", "a", False, 1, "hybrid", "intent", 1.0)

    assert store.list(limit=10) == [next_entry]
    assert next_entry.query_id == "query_000001"


def test_query_logs_do_not_store_raw_context_or_chunks() -> None:
    store = InMemoryQueryLogStore()

    entry = store.create_entry(
        user_id="finance_user",
        query="What is the invoice approval limit?",
        answer="Use the cited policy [1].",
        safe_abstain=False,
        citation_count=1,
        retrieval_mode="hybrid",
        intent="exact_lookup",
        latency_ms=3.2,
        debug={
            "retrieval_mode": "hybrid",
            "context_text": "raw context should not be stored",
            "focused_chunks": ["chunk text should not be stored"],
            "nested": {"chunk_id": "secret", "safe": True},
        },
    )

    serialized = str(entry)
    assert "raw context should not be stored" not in serialized
    assert "chunk text should not be stored" not in serialized
    assert "chunk_id" not in serialized
    assert entry.debug == {"retrieval_mode": "hybrid", "nested": {"safe": True}}
