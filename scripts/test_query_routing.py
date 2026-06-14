"""Print deterministic query analysis and retrieval-routing plans."""

from __future__ import annotations

import sys
from pathlib import Path
from pprint import pformat

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.context_engine.retrieval_router import RetrievalRouter

EXAMPLE_QUERIES = [
    "What is the invoice approval limit?",
    "How do we restore production after a bad release?",
    "NDA policy",
    "Show documents in finance",
    "What section explains data retention?",
    "How do I get paid back for travel costs?",
    "Compare remote work policy and contractor policy",
    "What are the steps for incident response?",
    "database backup schedule",
    "Which policies are latest version?",
]


def main() -> None:
    router = RetrievalRouter()
    for query in EXAMPLE_QUERIES:
        plan = router.build_plan(query)
        analysis = plan.analysis
        print(f"\nQuery: {query}")
        print(f"Intent: {analysis.intent}")
        print(f"Department hint: {analysis.department_hint}")
        print(f"Detected terms: {analysis.detected_terms}")
        print(f"Retrieval mode: {plan.retrieval_mode}")
        print(f"Reason: {plan.reason}")
        print(f"Filters: {pformat(plan.filters)}")
        print(f"candidate_k/top_k: {plan.candidate_k}/{plan.top_k}")


if __name__ == "__main__":
    main()
