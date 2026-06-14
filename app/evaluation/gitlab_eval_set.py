"""Deterministic eval set for local GitLab Handbook-style fixtures."""

from __future__ import annotations

from app.schemas import EvalExample


def get_gitlab_eval_set() -> list[EvalExample]:
    """Return offline eval examples for GitLab Handbook-style public docs."""
    return [
        _positive(
            "gitlab_001",
            "What does the handbook say about remote work?",
            ["GitLab Remote Work Handbook"],
            ["hr"],
            ["remote work", "handbook"],
            "hybrid",
        ),
        _positive(
            "gitlab_002",
            "How should distributed work be handled?",
            ["GitLab Remote Work Handbook", "GitLab Communication Handbook"],
            ["hr"],
            ["distributed work", "remote work"],
            "dense_only",
        ),
        _positive(
            "gitlab_003",
            "What does the handbook say about communication?",
            ["GitLab Communication Handbook"],
            ["hr"],
            ["communication", "handbook"],
            "dense_only",
        ),
        _positive(
            "gitlab_004",
            "How do teams document decisions and updates?",
            ["GitLab Communication Handbook"],
            ["hr"],
            ["document decisions", "updates"],
            "dense_only",
        ),
        _positive(
            "gitlab_005",
            "What is the onboarding process for team members?",
            ["GitLab Onboarding Handbook"],
            ["hr"],
            ["onboarding", "team members"],
            "hybrid",
        ),
        _positive(
            "gitlab_006",
            "How should a new team member start onboarding?",
            ["GitLab Onboarding Handbook"],
            ["hr"],
            ["new team member", "onboarding"],
            "hybrid",
        ),
        _positive(
            "gitlab_007",
            "What is the engineering development process?",
            ["GitLab Engineering Development Process"],
            ["engineering"],
            ["engineering", "development process"],
            "hybrid",
        ),
        _positive(
            "gitlab_008",
            "How do engineering changes move through review?",
            ["GitLab Engineering Development Process"],
            ["engineering"],
            ["engineering changes", "review"],
            "hybrid",
        ),
        _positive(
            "gitlab_009",
            "How should a bad production incident be handled?",
            ["GitLab Incident Management Handbook"],
            ["engineering"],
            ["production incident", "incident"],
            "hybrid",
        ),
        _positive(
            "gitlab_010",
            "What does incident management say about severity and mitigation?",
            ["GitLab Incident Management Handbook"],
            ["engineering"],
            ["incident management", "severity", "mitigation"],
            "hybrid",
        ),
        _positive(
            "gitlab_011",
            "What do security operations teams do?",
            ["GitLab Security Operations Handbook"],
            ["engineering"],
            ["security operations"],
            "dense_only",
        ),
        _positive(
            "gitlab_012",
            "How are security alerts triaged?",
            ["GitLab Security Operations Handbook"],
            ["engineering"],
            ["security alerts", "triage"],
            "dense_only",
        ),
        _positive(
            "gitlab_013",
            "How should expense reimbursement work?",
            ["GitLab Finance Expenses Handbook"],
            ["finance"],
            ["expense", "reimbursement"],
            "hybrid",
        ),
        _positive(
            "gitlab_014",
            "What does the finance handbook say about travel expenses?",
            ["GitLab Finance Expenses Handbook"],
            ["finance"],
            ["finance", "travel expenses"],
            "hybrid",
        ),
        _positive(
            "gitlab_015",
            "What are the privacy and compliance rules?",
            ["GitLab Legal Privacy And Compliance Handbook"],
            ["legal"],
            ["privacy", "compliance"],
            "hybrid",
        ),
        _positive(
            "gitlab_016",
            "How should legal review data protection obligations?",
            ["GitLab Legal Privacy And Compliance Handbook"],
            ["legal"],
            ["legal", "data protection"],
            "hybrid",
        ),
        _impossible(
            "gitlab_017",
            "What is the company's cafeteria lunch menu?",
        ),
        _impossible(
            "gitlab_018",
            "What is the unreleased acquisition plan?",
        ),
    ]


def _positive(
    example_id: str,
    question: str,
    titles: list[str],
    departments: list[str],
    terms: list[str],
    mode: str,
) -> EvalExample:
    return EvalExample(
        example_id=example_id,
        question=question,
        user_id="intern_user",
        expected_document_titles=titles,
        expected_departments=departments,
        expected_retrieval_mode=mode,
        expected_access_allowed=True,
        answer_should_abstain=False,
        expected_terms=terms,
    )


def _impossible(example_id: str, question: str) -> EvalExample:
    return EvalExample(
        example_id=example_id,
        question=question,
        user_id="intern_user",
        expected_document_titles=[],
        expected_departments=[],
        expected_retrieval_mode="dense_only",
        expected_access_allowed=True,
        answer_should_abstain=True,
        expected_terms=[],
        notes="Out-of-corpus question for smoke-testing abstention behavior.",
    )
