"""Smoke test optional SQLite persistence without running the API server."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from time import perf_counter

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main() -> int:
    os.environ.setdefault("ECE_STORAGE_BACKEND", "sqlite")
    os.environ.setdefault("ECE_SQLITE_PATH", str(PROJECT_ROOT / "data" / "state" / "enterprise_context_engine.db"))

    from app.evaluation.eval_runner import EvalRunner
    from app.evaluation.sample_eval_set import get_sample_eval_set
    from app.generation.answer_generator import AnswerGenerator
    from app.storage.app_state import (
        SAMPLE_DOCS,
        create_query_log,
        get_sqlite_store,
        load_data_source,
        reset_app_state,
        save_eval_summary,
    )
    from app.storage.sqlite_store import SQLiteStore
    from scripts.create_sample_docs import create_sample_docs

    create_sample_docs()
    reset_app_state()
    store = get_sqlite_store()
    store.clear_all()

    state = load_data_source(SAMPLE_DOCS)
    started = perf_counter()
    answer = AnswerGenerator().generate(
        "What is the invoice approval limit?",
        "finance_user",
        state.chunks,
        top_k=5,
    )
    latency_ms = (perf_counter() - started) * 1000
    create_query_log(
        user_id="finance_user",
        query=answer.query,
        answer=answer.answer,
        safe_abstain=answer.safe_abstain,
        citation_count=len(answer.citations),
        retrieval_mode=answer.debug.get("retrieval_mode"),
        intent=answer.debug.get("intent"),
        latency_ms=latency_ms,
        debug=answer.debug,
    )

    summary = EvalRunner(state.chunks).run(get_sample_eval_set())
    save_eval_summary(SAMPLE_DOCS, summary)

    reopened = SQLiteStore(store.db_path)
    reopened.initialize()
    documents = reopened.load_documents()
    chunks = reopened.load_chunks()
    logs = reopened.list_query_logs(limit=10)
    latest_eval = reopened.load_latest_eval_summary()

    assert documents
    assert chunks
    assert logs
    assert latest_eval is not None

    print("SQLite persistence demo")
    print(f"Database: {store.db_path}")
    print(f"Documents persisted: {len(documents)}")
    print(f"Chunks persisted: {len(chunks)}")
    print(f"Query logs persisted: {len(logs)}")
    print(f"Latest eval source: {latest_eval['source']}")
    print(f"Latest eval pass rate: {latest_eval['metrics']['pass_rate']:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
