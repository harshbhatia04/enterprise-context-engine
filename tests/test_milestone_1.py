from pathlib import Path

from app.security.users import get_user, list_users
from scripts.create_sample_docs import create_sample_docs


REQUIRED_FRONTMATTER_FIELDS = {
    "title",
    "department",
    "access_level",
    "version",
    "effective_date",
    "document_type",
}


def parse_frontmatter(markdown: str) -> dict[str, str]:
    lines = markdown.splitlines()
    assert lines[0] == "---"
    metadata = {}
    for line in lines[1:]:
        if line == "---":
            break
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip().strip('"')
    return metadata


def test_fake_users_are_available() -> None:
    users = {user["user_id"]: user for user in list_users()}

    assert set(users) == {
        "admin_user",
        "hr_user",
        "finance_user",
        "engineer_user",
        "legal_user",
        "intern_user",
    }
    assert users["admin_user"]["access_levels"] == ["all"]
    assert users["intern_user"]["allowed_departments"] == ["general", "public"]
    assert get_user("engineer_user")["department"] == "engineering"


def test_sample_doc_generator_creates_24_markdown_docs(tmp_path: Path) -> None:
    created = create_sample_docs(tmp_path)

    assert len(created) == 24
    assert len(list(tmp_path.glob("*.md"))) == 24


def test_generated_docs_have_required_frontmatter(tmp_path: Path) -> None:
    created = create_sample_docs(tmp_path)

    departments = set()
    for path in created:
        metadata = parse_frontmatter(path.read_text(encoding="utf-8"))
        assert REQUIRED_FRONTMATTER_FIELDS.issubset(metadata)
        assert metadata["access_level"] == metadata["department"]
        assert metadata["version"] == "1.0"
        assert metadata["effective_date"] == "2026-01-01"
        departments.add(metadata["department"])

    assert departments == {"hr", "finance", "engineering", "legal"}
