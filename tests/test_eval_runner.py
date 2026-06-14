import json
from dataclasses import asdict
from pathlib import Path

import pytest

from app.evaluation.eval_runner import EvalRunner
from app.evaluation.sample_eval_set import get_sample_eval_set
from app.ingestion.pipeline import ingest_directory
from app.schemas import EvalExampleResult, EvalSummary
from scripts.create_sample_docs import create_sample_docs


@pytest.fixture()
def eval_runner(tmp_path: Path) -> EvalRunner:
    create_sample_docs(tmp_path)
    _, chunks = ingest_directory(tmp_path)
    return EvalRunner(chunks)


def test_get_sample_eval_set_returns_at_least_30_examples() -> None:
    examples = get_sample_eval_set()

    assert len(examples) >= 30
    assert len({example.example_id for example in examples}) == len(examples)


def test_run_example_returns_eval_example_result(eval_runner: EvalRunner) -> None:
    example = get_sample_eval_set()[0]

    result = eval_runner.run_example(example)

    assert isinstance(result, EvalExampleResult)
    assert result.example_id == example.example_id
    assert "document_hit" in result.metrics
    assert result.latency_ms >= 0


def test_authorized_finance_example_has_expected_metrics(eval_runner: EvalRunner) -> None:
    example = next(item for item in get_sample_eval_set() if item.example_id == "eval_001")

    result = eval_runner.run_example(example)

    assert result.safe_abstain is False
    assert result.metrics["citation_presence"] is True
    assert result.metrics["document_hit"] or result.metrics["department_hit"]


def test_unauthorized_intern_finance_example_safe_abstains(eval_runner: EvalRunner) -> None:
    example = next(item for item in get_sample_eval_set() if item.example_id == "eval_005")

    result = eval_runner.run_example(example)

    assert result.safe_abstain is True
    assert result.citations == []
    assert result.metrics["restricted_leak_detected"] is False
    assert result.passed is True


def test_eval_summary_metrics_include_required_keys(eval_runner: EvalRunner) -> None:
    examples = [
        next(item for item in get_sample_eval_set() if item.example_id == "eval_001"),
        next(item for item in get_sample_eval_set() if item.example_id == "eval_005"),
    ]

    summary = eval_runner.run(examples)

    assert isinstance(summary, EvalSummary)
    assert "pass_rate" in summary.metrics
    assert "restricted_leak_rate" in summary.metrics
    assert summary.total_examples == len(examples)


def test_eval_summary_json_can_be_serialized(eval_runner: EvalRunner) -> None:
    examples = get_sample_eval_set()[:3]
    summary = eval_runner.run(examples)

    encoded = json.dumps(asdict(summary))

    assert "total_examples" in encoded


def test_eval_runner_does_not_require_api_keys(monkeypatch: pytest.MonkeyPatch, eval_runner: EvalRunner) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    example = next(item for item in get_sample_eval_set() if item.example_id == "eval_001")

    result = eval_runner.run_example(example)

    assert result.answer
    assert result.debug["answer_debug"]["model_name"] == "mock-llm"
