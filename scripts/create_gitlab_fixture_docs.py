"""Create local GitLab Handbook-style fixture documents for demos and tests."""

from __future__ import annotations

import sys
from pathlib import Path
from textwrap import dedent

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

GITLAB_FIXTURE_DIR = PROJECT_ROOT / "data" / "real_sources" / "gitlab_handbook"

FIXTURES = [
    (
        "GitLab Remote Work Handbook",
        "hr",
        "remote-work",
        "Remote Work Practices",
        "Team members document decisions, prefer asynchronous updates, and make working agreements visible across time zones.",
    ),
    (
        "GitLab Communication Handbook",
        "hr",
        "communication",
        "Communication Norms",
        "Teams use written updates, clear ownership, and public-by-default decision records when information can be shared.",
    ),
    (
        "GitLab Onboarding Handbook",
        "hr",
        "onboarding",
        "Onboarding Plan",
        "New team members follow a structured onboarding issue, meet their manager, and learn handbook-first workflows.",
    ),
    (
        "GitLab Engineering Development Process",
        "engineering",
        "engineering-development-process",
        "Development Workflow",
        "Engineering changes move through issues, merge requests, code review, automated tests, and documented release checks.",
    ),
    (
        "GitLab Incident Management Handbook",
        "engineering",
        "incident-management",
        "Incident Response",
        "Incident commanders coordinate response, severity, communication, mitigation, and follow-up review after production events.",
    ),
    (
        "GitLab Security Operations Handbook",
        "engineering",
        "security-operations",
        "Security Operations",
        "Security operations teams triage alerts, document risk, coordinate engineering remediation, and track production impact.",
    ),
    (
        "GitLab Finance Expenses Handbook",
        "finance",
        "finance-expenses",
        "Expense Guidelines",
        "Team members submit business expenses with receipts, purpose, approval context, and travel or procurement details.",
    ),
    (
        "GitLab Legal Privacy And Compliance Handbook",
        "legal",
        "legal-privacy-compliance",
        "Privacy And Compliance",
        "Legal teams review privacy, compliance, contracts, data protection, and customer obligations before sensitive commitments.",
    ),
]


def create_gitlab_fixture_docs(output_dir: Path = GITLAB_FIXTURE_DIR) -> list[Path]:
    """Create deterministic synthetic GitLab Handbook-style Markdown fixtures."""
    output_dir.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []
    for title, department, slug, section, detail in FIXTURES:
        path = output_dir / f"{slug}.md"
        path.write_text(_document_text(title, department, section, detail), encoding="utf-8")
        created.append(path)
    readme_path = output_dir / "README.md"
    if not readme_path.exists():
        readme_path.write_text(
            dedent(
                """\
                # GitLab Handbook Fixture Directory

                This directory stores local Markdown files for the GitLab Handbook ingestion MVP.
                The generated fixture files are synthetic excerpts inspired by public handbook
                structure. They are not official GitLab content.
                """
            ),
            encoding="utf-8",
        )
    return created


def _document_text(title: str, department: str, section: str, detail: str) -> str:
    return dedent(
        f"""\
        ---
        title: "{title}"
        department: "{department}"
        access_level: "public"
        version: "public"
        effective_date: "unknown"
        document_type: "handbook"
        source_name: "gitlab_handbook"
        source_url: "https://handbook.gitlab.com/"
        ---

        # {title}

        **Fixture note:** This is synthetic fixture text inspired by public handbook structure. It is not official GitLab content.

        ## Purpose

        This fixture represents public enterprise handbook guidance for the {department} department. It is designed for deterministic local ingestion tests and portfolio demos.

        ## {section}

        {detail}

        ## Operating Practices

        Handbook-first teams keep guidance discoverable, update ownership clear, and decision records accessible to people who need the information.
        """
    )


def main() -> None:
    created = create_gitlab_fixture_docs()
    print(f"Created {len(created)} GitLab Handbook fixture documents in {GITLAB_FIXTURE_DIR}")


if __name__ == "__main__":
    main()
