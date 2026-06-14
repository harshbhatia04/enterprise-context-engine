"""Run deterministic evaluation for selected data sources."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import EVAL_DATA_DIR
from app.evaluation.eval_runner import EvalRunner
from app.evaluation.gitlab_eval_set import get_gitlab_eval_set
from app.evaluation.sample_eval_set import get_sample_eval_set
from app.schemas import Chunk, EvalExample, EvalSummary
from app.storage.app_state import (
    COMBINED,
    GITLAB_HANDBOOK,
    SAMPLE_DOCS,
    load_gitlab_handbook_docs,
    load_sample_docs,
    save_eval_summary,
)
from scripts.create_gitlab_fixture_docs import create_gitlab_fixture_docs

RESULT_PATHS = {
    SAMPLE_DOCS: EVAL_DATA_DIR / "latest_eval_results.json",
    GITLAB_HANDBOOK: EVAL_DATA_DIR / "latest_gitlab_eval_results.json",
    COMBINED: EVAL_DATA_DIR / "latest_combined_eval_results.json",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deterministic Enterprise Context Engine evals.")
    parser.add_argument(
        "--source",
        choices=[SAMPLE_DOCS, GITLAB_HANDBOOK, COMBINED],
        default=SAMPLE_DOCS,
        help="Data source eval to run. Defaults to sample_docs.",
    )
    args = parser.parse_args()

    summary, result_path = run_eval_for_source(args.source)
    print_eval_summary(args.source, summary, result_path)
    return 0


def run_eval_for_source(source: str) -> tuple[EvalSummary, Path]:
    """Run one source-specific deterministic eval and persist JSON results."""
    chunks, examples = _load_eval_inputs(source)
    summary = EvalRunner(chunks).run(examples)
    save_eval_summary(source, summary)
    result_path = RESULT_PATHS[source]
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(
        json.dumps(asdict(summary), indent=2),
        encoding="utf-8",
    )
    return summary, result_path


def print_eval_summary(source: str, summary: EvalSummary, result_path: Path) -> None:
    """Print a compact human-readable eval summary."""
    title = "Enterprise Context Engine Evaluation"
    if source == GITLAB_HANDBOOK:
        title = "GitLab Handbook-style Evaluation"
    elif source == COMBINED:
        title = "Combined Corpus Evaluation"

    print(f"{title}\n")
    print(f"Source: {source}")
    print(f"Total examples: {summary.total_examples}")
    print(f"Passed: {summary.passed_examples}")
    print(f"Failed: {summary.failed_examples}")
    print(f"Pass rate: {summary.metrics['pass_rate']:.2f}\n")
    print("Metrics:")
    _print_metric("Retrieval document hit rate", summary.metrics["retrieval_document_hit_rate"])
    _print_metric("Retrieval department hit rate", summary.metrics["retrieval_department_hit_rate"])
    _print_metric("Mean Recall@5", summary.metrics["mean_recall_at_5"])
    _print_metric("Mean MRR", summary.metrics["mean_mrr"])
    _print_metric("Mean nDCG@5", summary.metrics["mean_ndcg_at_5"])
    _print_metric("Citation presence rate", summary.metrics["citation_presence_rate"])
    _print_metric("Abstention accuracy", summary.metrics["abstention_accuracy"])
    _print_metric("Grounded answer rate", summary.metrics["grounded_answer_rate"])
    _print_metric("Restricted leak rate", summary.metrics["restricted_leak_rate"])
    _print_metric("Retrieval mode accuracy", summary.metrics["retrieval_mode_accuracy"])
    print(f"- Average latency ms: {summary.metrics['average_latency_ms']:.2f}")
    print(f"- Authorized count: {summary.metrics['authorized_count']}")
    print(f"- Unauthorized count: {summary.metrics['unauthorized_count']}")
    print(f"\nWrote JSON results to: {result_path}")

    failed = [result for result in summary.results if not result.passed]
    if failed:
        print("\nFailed examples:")
        for result in failed:
            reasons = "; ".join(result.failure_reasons)
            print(f"- {result.example_id}: {reasons}")
    else:
        print("\nFailed examples: none")


def _load_eval_inputs(source: str) -> tuple[list[Chunk], list[EvalExample]]:
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
    raise ValueError(f"Unsupported eval source: {source}")


def _print_metric(label: str, value: float) -> None:
    print(f"- {label}: {value:.2f}")


if __name__ == "__main__":
    raise SystemExit(main())
