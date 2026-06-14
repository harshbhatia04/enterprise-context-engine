"""Evaluation routes for deterministic pipeline scoring."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.evaluation.eval_runner import EvalRunner
from app.evaluation.gitlab_eval_set import get_gitlab_eval_set
from app.evaluation.sample_eval_set import get_sample_eval_set
from app.storage.app_state import (
    COMBINED,
    GITLAB_HANDBOOK,
    SAMPLE_DOCS,
    get_app_state,
    load_latest_eval_summary,
    load_gitlab_handbook_docs,
    load_sample_docs,
    save_eval_summary,
)
from scripts.create_gitlab_fixture_docs import create_gitlab_fixture_docs

router = APIRouter(tags=["evaluation"])


@router.post("/evaluate")
def evaluate(source: str = Query(default=SAMPLE_DOCS)) -> dict:
    """Run the bundled deterministic evaluation set."""
    normalized_source = str(source or SAMPLE_DOCS).strip().lower()
    try:
        chunks, examples = _load_eval_inputs(normalized_source)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    summary = EvalRunner(chunks).run(examples)
    save_eval_summary(normalized_source, summary)
    return {
        "source": normalized_source,
        "total_examples": summary.total_examples,
        "passed_examples": summary.passed_examples,
        "failed_examples": summary.failed_examples,
        "metrics": summary.metrics,
    }


@router.get("/metrics")
def metrics() -> dict:
    """Return the latest evaluation metrics if an eval has run."""
    state = get_app_state()
    if state.last_eval_summary is None:
        persisted = load_latest_eval_summary()
        if persisted is not None:
            return {
                "source": persisted["source"],
                "total_examples": persisted["total_examples"],
                "passed_examples": persisted["passed_examples"],
                "failed_examples": persisted["failed_examples"],
                "metrics": persisted["metrics"],
            }
        return {"status": "no_evaluation_run"}
    return {
        "source": state.last_eval_source or SAMPLE_DOCS,
        "total_examples": state.last_eval_summary.total_examples,
        "passed_examples": state.last_eval_summary.passed_examples,
        "failed_examples": state.last_eval_summary.failed_examples,
        "metrics": state.last_eval_summary.metrics,
    }


def _load_eval_inputs(source: str):
    if source == SAMPLE_DOCS:
        _, chunks = load_sample_docs()
        return chunks, get_sample_eval_set()
    if source == GITLAB_HANDBOOK:
        create_gitlab_fixture_docs()
        _, chunks = load_gitlab_handbook_docs()
        return chunks, get_gitlab_eval_set()
    if source == COMBINED:
        create_gitlab_fixture_docs()
        _, sample_chunks = load_sample_docs()
        _, gitlab_chunks = load_gitlab_handbook_docs()
        return [*sample_chunks, *gitlab_chunks], [*get_sample_eval_set(), *get_gitlab_eval_set()]
    raise ValueError(
        f"Unsupported eval source: {source}. "
        f"Allowed sources: {SAMPLE_DOCS}, {GITLAB_HANDBOOK}, {COMBINED}"
    )
