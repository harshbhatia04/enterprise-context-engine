import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from app.evaluation.eval_runner import EvalRunner
from app.evaluation.gitlab_eval_set import get_gitlab_eval_set
from app.ingestion.real_data.gitlab_handbook import ingest_gitlab_handbook_directory
from app.main import app
from app.storage.app_state import reset_app_state
from scripts.create_gitlab_fixture_docs import create_gitlab_fixture_docs

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_gitlab_eval_set_returns_at_least_16_examples() -> None:
    assert len(get_gitlab_eval_set()) >= 16


def test_gitlab_eval_examples_have_unique_ids() -> None:
    examples = get_gitlab_eval_set()

    assert len({example.example_id for example in examples}) == len(examples)


def test_most_gitlab_eval_examples_use_intern_user() -> None:
    examples = get_gitlab_eval_set()
    intern_count = sum(1 for example in examples if example.user_id == "intern_user")

    assert intern_count / len(examples) >= 0.75


def test_most_positive_gitlab_examples_are_accessible() -> None:
    positive = [example for example in get_gitlab_eval_set() if not example.answer_should_abstain]

    assert positive
    assert sum(1 for example in positive if example.expected_access_allowed) / len(positive) >= 0.9


def test_running_gitlab_eval_over_fixture_docs_returns_summary() -> None:
    create_gitlab_fixture_docs()
    _, chunks = ingest_gitlab_handbook_directory(PROJECT_ROOT / "data" / "real_sources" / "gitlab_handbook")

    summary = EvalRunner(chunks).run(get_gitlab_eval_set())

    assert summary.total_examples == len(get_gitlab_eval_set())
    assert "pass_rate" in summary.metrics
    assert "mean_recall_at_5" in summary.metrics
    assert "citation_presence_rate" in summary.metrics
    assert "restricted_leak_rate" in summary.metrics
    assert summary.metrics["pass_rate"] >= 0.94
    assert summary.metrics["restricted_leak_rate"] == 0.0


def test_gitlab_impossible_questions_safe_abstain() -> None:
    create_gitlab_fixture_docs()
    _, chunks = ingest_gitlab_handbook_directory(PROJECT_ROOT / "data" / "real_sources" / "gitlab_handbook")
    examples = [example for example in get_gitlab_eval_set() if example.answer_should_abstain]

    summary = EvalRunner(chunks).run(examples)

    assert examples
    assert summary.metrics["abstention_accuracy"] == 1.0
    assert all(result.safe_abstain for result in summary.results)
    assert all(result.citations == [] for result in summary.results)


def test_gitlab_restricted_leak_rate_remains_zero() -> None:
    create_gitlab_fixture_docs()
    _, chunks = ingest_gitlab_handbook_directory(PROJECT_ROOT / "data" / "real_sources" / "gitlab_handbook")

    summary = EvalRunner(chunks).run(get_gitlab_eval_set())

    assert summary.metrics["restricted_leak_rate"] == 0.0


def test_run_eval_sample_docs_source_still_works() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/run_eval.py", "--source", "sample_docs"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert result.returncode == 0
    assert "Source: sample_docs" in result.stdout
    assert "Pass rate: 1.00" in result.stdout


def test_run_eval_gitlab_source_works() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/run_eval.py", "--source", "gitlab_handbook"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert result.returncode == 0
    assert "Source: gitlab_handbook" in result.stdout
    assert "Restricted leak rate: 0.00" in result.stdout


def test_api_evaluate_gitlab_source_works() -> None:
    reset_app_state()
    create_gitlab_fixture_docs()
    client = TestClient(app)

    response = client.post("/evaluate?source=gitlab_handbook")
    payload = response.json()

    assert response.status_code == 200
    assert payload["source"] == "gitlab_handbook"
    assert payload["metrics"]["pass_rate"] >= 0.94
    assert payload["metrics"]["restricted_leak_rate"] == 0.0

    metrics = client.get("/metrics").json()
    assert metrics["source"] == "gitlab_handbook"


def test_dashboard_code_contains_evaluation_source_selection() -> None:
    dashboard = (PROJECT_ROOT / "dashboard" / "streamlit_app.py").read_text(encoding="utf-8")

    assert "Evaluation Source" in dashboard
    assert "gitlab_handbook" in dashboard
    assert "/evaluate?source=" in dashboard
