from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def read(relative_path: str) -> str:
    return (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")


def test_demo_asset_docs_exist() -> None:
    for relative_path in [
        "docs/DEMO_VIDEO_SCRIPT.md",
        "docs/GITHUB_SHOWCASE.md",
        "docs/RELEASE_NOTES.md",
        "assets/screenshots/README.md",
        "assets/screenshots/.gitkeep",
    ]:
        assert (PROJECT_ROOT / relative_path).exists()


def test_readme_links_demo_assets_and_status() -> None:
    text = read("README.md")

    assert "Demo Video Script" in text
    assert "docs/DEMO_VIDEO_SCRIPT.md" in text
    assert "Portfolio status" in text


def test_release_notes_contain_final_metrics() -> None:
    text = read("docs/RELEASE_NOTES.md")

    assert "v1.0.0" in text
    assert "37/37" in text
    assert "18/18" in text
    assert "restricted leak rate" in text


def test_demo_video_script_contains_key_demo_queries() -> None:
    text = read("docs/DEMO_VIDEO_SCRIPT.md")

    assert "invoice approval limit" in text
    assert "remote work" in text
    assert "unreleased acquisition plan" in text
    assert "evidence gate" in text


def test_github_showcase_contains_suggested_topics() -> None:
    text = read("docs/GITHUB_SHOWCASE.md")

    assert "Suggested Topics" in text
    assert "context-engineering" in text
    assert "hybrid-search" in text
