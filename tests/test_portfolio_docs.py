from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (PROJECT_ROOT / path).read_text(encoding="utf-8")


def test_final_portfolio_docs_exist() -> None:
    for relative_path in [
        "docs/FINAL_REPORT.md",
        "docs/INTERVIEW_GUIDE.md",
        "docs/RESUME_BULLETS.md",
        "docs/ROADMAP.md",
        "docs/LIMITATIONS.md",
        "docs/RELEASE_CHECKLIST.md",
    ]:
        assert (PROJECT_ROOT / relative_path).exists()


def test_readme_contains_portfolio_positioning() -> None:
    text = read("README.md")

    assert "Enterprise Context Engine" in text
    assert "Permission-aware context engineering" in text
    assert "Interview Pitch" in text


def test_final_report_contains_metrics() -> None:
    text = read("docs/FINAL_REPORT.md")

    assert "sample_docs" in text
    assert "gitlab_handbook" in text
    assert "restricted leak rate" in text


def test_interview_guide_contains_deep_dive_topics() -> None:
    text = read("docs/INTERVIEW_GUIDE.md")

    assert "Why not naive RAG" in text
    assert "access control" in text
    assert "evidence gate" in text


def test_resume_bullets_contains_target_roles() -> None:
    text = read("docs/RESUME_BULLETS.md")

    assert "ML Engineer" in text
    assert "GenAI Engineer" in text


def test_screenshot_placeholder_exists() -> None:
    assert (PROJECT_ROOT / "assets" / "screenshots" / "README.md").exists()
