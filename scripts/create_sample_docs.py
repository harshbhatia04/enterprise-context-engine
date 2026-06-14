"""Generate fake enterprise Markdown documents for the MVP."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DOCS_DIR = PROJECT_ROOT / "data" / "sample_docs"

DOCUMENTS = [
    ("hr", "Leave Policy", "leave-policy", "policy", "Planned Time Away", "Balance Tracking"),
    ("hr", "Reimbursement Policy", "reimbursement-policy", "policy", "Eligible Expenses", "Submission Requirements"),
    ("hr", "Contractor Policy", "contractor-policy", "policy", "Engagement Rules", "Access Boundaries"),
    ("hr", "Remote Work Policy", "remote-work-policy", "policy", "Eligibility", "Workspace Expectations"),
    ("hr", "Performance Review Policy", "performance-review-policy", "policy", "Review Cycle", "Calibration"),
    ("hr", "Employee Onboarding Policy", "employee-onboarding-policy", "policy", "Preboarding", "First Week Plan"),
    ("finance", "Invoice Approval Policy", "invoice-approval-policy", "policy", "Approval Limits", "Exception Handling"),
    ("finance", "Vendor Payment Policy", "vendor-payment-policy", "policy", "Payment Schedule", "Vendor Validation"),
    ("finance", "Budget Approval Workflow", "budget-approval-workflow", "workflow", "Budget Tiers", "Approval Routing"),
    ("finance", "Expense Limits", "expense-limits", "policy", "Spend Categories", "Receipt Requirements"),
    ("finance", "Audit Procedure", "audit-procedure", "procedure", "Evidence Collection", "Control Review"),
    ("finance", "Procurement Policy", "procurement-policy", "policy", "Sourcing Rules", "Purchase Orders"),
    ("engineering", "Deployment Guide", "deployment-guide", "guide", "Release Preparation", "Post-deployment Verification"),
    ("engineering", "Rollback Procedure", "rollback-procedure", "procedure", "Rollback Decision", "Emergency Rollback Steps"),
    ("engineering", "Incident Response Guide", "incident-response-guide", "guide", "Severity Levels", "Communication Plan"),
    ("engineering", "API Authentication Guide", "api-authentication-guide", "guide", "Token Handling", "Service Credentials"),
    ("engineering", "Database Backup Policy", "database-backup-policy", "policy", "Backup Schedule", "Restore Testing"),
    ("engineering", "Production Access Policy", "production-access-policy", "policy", "Access Requests", "Privileged Sessions"),
    ("legal", "NDA Policy", "nda-policy", "policy", "Required Agreements", "Mutual NDA Review"),
    ("legal", "Vendor Contract Review Policy", "vendor-contract-review-policy", "policy", "Review Intake", "Negotiation Thresholds"),
    ("legal", "Data Privacy Policy", "data-privacy-policy", "policy", "Personal Data Handling", "Privacy Reviews"),
    ("legal", "Retention Policy", "retention-policy", "policy", "Retention Periods", "Legal Holds"),
    ("legal", "Compliance Checklist", "compliance-checklist", "checklist", "Quarterly Evidence", "Owner Attestations"),
    ("legal", "Security Addendum Policy", "security-addendum-policy", "policy", "Security Terms", "Customer Exceptions"),
]


def frontmatter(title: str, department: str, document_type: str) -> str:
    return dedent(
        f"""\
        ---
        title: "{title}"
        department: "{department}"
        access_level: "{department}"
        version: "1.0"
        effective_date: "2026-01-01"
        document_type: "{document_type}"
        ---
        """
    )


def body(title: str, department: str, primary_section: str, secondary_section: str) -> str:
    department_label = department.title()
    return dedent(
        f"""\

        # {title}

        ## Purpose

        This document defines how the {department_label} team applies the {title.lower()} in daily operations. It gives managers and contributors a consistent operating reference for decisions, approvals, and audit-friendly documentation.

        ## Scope

        The policy applies to active employees, approved contractors, and business processes owned by the {department_label} department. Requests outside this scope require review by the document owner before action is taken.

        ## {primary_section}

        Teams should capture the business reason, responsible owner, approval evidence, and expected completion date before work proceeds. Routine requests may follow the standard path, while sensitive or high-impact requests require manager review and documented approval.

        ## {secondary_section}

        Owners must keep records current, use the approved tracking system, and escalate exceptions within one business day. Any exception should include a short risk summary, the mitigation plan, and the approver who accepted the risk.

        ## Review And Updates

        The document owner reviews this guidance quarterly. Material changes are announced to impacted teams, and the prior version remains available for audit reference.
        """
    )


def build_document(title: str, department: str, document_type: str, primary_section: str, secondary_section: str) -> str:
    return frontmatter(title, department, document_type) + body(title, department, primary_section, secondary_section)


def create_sample_docs(output_dir: Path = SAMPLE_DOCS_DIR) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []
    for department, title, slug, document_type, primary_section, secondary_section in DOCUMENTS:
        path = output_dir / f"{department}-{slug}.md"
        path.write_text(
            build_document(title, department, document_type, primary_section, secondary_section),
            encoding="utf-8",
        )
        created.append(path)
    return created


def main() -> None:
    created = create_sample_docs()
    print(f"Created {len(created)} sample documents in {SAMPLE_DOCS_DIR}")


if __name__ == "__main__":
    main()
