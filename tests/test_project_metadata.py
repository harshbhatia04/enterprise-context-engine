from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_readme_exists_and_contains_portfolio_sections() -> None:
    readme = PROJECT_ROOT / "README.md"
    text = readme.read_text(encoding="utf-8")

    assert "Enterprise Context Engine" in text
    assert "context engineering" in text.lower()
    assert "Interview Pitch" in text
    assert "tests-233" in text or "Tests" in text


def test_docs_files_exist() -> None:
    docs = PROJECT_ROOT / "docs"

    assert (PROJECT_ROOT / "SECURITY.md").exists()
    assert (docs / "ARCHITECTURE.md").exists()
    assert (docs / "DEMO_SCRIPT.md").exists()
    assert (docs / "EVALUATION.md").exists()
    assert (docs / "SECURITY.md").exists()


def test_docker_files_exist() -> None:
    assert (PROJECT_ROOT / "Dockerfile").exists()
    assert (PROJECT_ROOT / "Dockerfile.dashboard").exists()
    assert (PROJECT_ROOT / "docker-compose.yml").exists()


def test_env_example_contains_mock_mode() -> None:
    text = (PROJECT_ROOT / ".env.example").read_text(encoding="utf-8")

    assert "ECE_LLM_MODE=mock" in text


def test_makefile_contains_docker_up() -> None:
    text = (PROJECT_ROOT / "Makefile").read_text(encoding="utf-8")

    assert "docker-up" in text


def test_ci_and_quality_files_exist() -> None:
    assert (PROJECT_ROOT / ".github" / "workflows" / "ci.yml").exists()
    assert (PROJECT_ROOT / ".editorconfig").exists()
    assert (PROJECT_ROOT / "CONTRIBUTING.md").exists()
    assert (PROJECT_ROOT / "requirements-dev.txt").exists()
    assert (PROJECT_ROOT / "pyproject.toml").exists()
    assert (PROJECT_ROOT / "scripts" / "check_project.py").exists()


def test_ignore_files_protect_local_artifacts() -> None:
    gitignore = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8")
    dockerignore = (PROJECT_ROOT / ".dockerignore").read_text(encoding="utf-8")

    for pattern in ("*.db", "data/state/", "data/eval/latest*.json", ".ruff_cache/"):
        assert pattern in gitignore

    for pattern in ("*.db", "data/state/", "data/eval/*.json", ".ruff_cache/"):
        assert pattern in dockerignore


def test_no_stale_milestone_placeholder_markers() -> None:
    stale_marker = "placeholder for " + "Milestone"
    offenders = []
    for path in (PROJECT_ROOT / "app").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if stale_marker in text:
            offenders.append(str(path.relative_to(PROJECT_ROOT)))

    assert not offenders, f"Stale milestone placeholder markers remain: {offenders}"
