"""Deterministic query analysis for retrieval routing."""

from __future__ import annotations

import re

from app.schemas import QueryAnalysis

INTENT_PRIORITY = [
    "metadata_request",
    "section_request",
    "comparison",
    "troubleshooting",
    "procedure",
    "exact_lookup",
    "policy_question",
]

INTENT_SIGNALS: dict[str, tuple[str, ...]] = {
    "metadata_request": (
        "list documents",
        "show documents",
        "show policies",
        "which documents",
        "what documents",
        "documents in",
        "latest version",
        "effective date",
        "current version",
        "version",
    ),
    "section_request": ("section", "clause", "heading", "part", "chapter"),
    "comparison": ("compare", "difference", "versus", "vs", "which is better", "between"),
    "troubleshooting": (
        "error",
        "failed",
        "failure",
        "outage",
        "incident",
        "broken",
        "not working",
        "severity",
        "downtime",
    ),
    "procedure": (
        "how do",
        "how should",
        "what should",
        "steps",
        "step",
        "process",
        "workflow",
        "after",
        "rollback",
        "deployment",
    ),
    "policy_question": (
        "what is",
        "what are",
        "allowed",
        "policy",
        "rules",
        "limits",
        "limit",
        "requirements",
        "can i",
        "can we",
    ),
}

DEPARTMENT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "hr": (
        "leave",
        "reimbursement",
        "expense",
        "remote work",
        "performance",
        "contractor",
        "onboarding",
        "employee",
        "travel costs",
        "paid back",
        "work from home",
        "wfh",
    ),
    "finance": (
        "invoice",
        "vendor payment",
        "budget",
        "audit",
        "procurement",
        "approval limit",
        "payment",
        "finance",
    ),
    "engineering": (
        "deployment",
        "rollback",
        "incident",
        "api",
        "authentication",
        "database",
        "backup",
        "production",
        "outage",
        "severity",
        "engineering",
        "release",
    ),
    "legal": (
        "nda",
        "confidentiality",
        "contract",
        "privacy",
        "retention",
        "compliance",
        "legal",
        "security addendum",
    ),
}

IMPORTANT_TERMS = (
    "invoice approval",
    "vendor payment",
    "database backup",
    "retention policy",
    "rollback procedure",
    "remote work",
    "incident response",
    "api authentication",
    "production access",
    "security addendum",
    "data retention",
    "nda",
    "rollback",
    "retention",
    "database",
    "backup",
    "invoice",
    "reimbursement",
    "confidentiality",
    "contractor",
    "deployment",
    "incident",
)

EXACT_PHRASES = (
    "invoice approval",
    "vendor payment",
    "database backup",
    "retention policy",
    "rollback procedure",
    "remote work policy",
    "incident response",
    "api authentication",
    "production access",
    "security addendum",
    "nda policy",
)

ACRONYMS = {"nda", "sla", "api", "sso", "soc2"}
EXACT_WORDS = {"exact", "title", "named", "section", "clause", "limit", "limits", "version"}
SEMANTIC_PHRASES = (
    "how do we",
    "how do i",
    "what should we",
    "can i",
    "can we",
    "get paid back",
    "paid back",
    "work from home",
    "bad release",
    "keep records",
    "restore production",
    "records be preserved",
)
METADATA_STRONG_SIGNALS = (
    "list documents",
    "show documents",
    "which documents",
    "what documents",
    "show policies",
    "latest version",
    "effective date",
    "documents in",
    "current version",
)
SECTION_SIGNALS = {"section", "clause", "heading", "part", "chapter"}


def normalize_query(query: str) -> str:
    """Lowercase and collapse whitespace for deterministic rules."""
    return " ".join(query.lower().strip().split())


def _contains_phrase(query: str, phrase: str) -> bool:
    if " " in phrase:
        return phrase in query
    return re.search(rf"\b{re.escape(phrase)}\b", query) is not None


def _count_department_matches(query: str) -> dict[str, int]:
    return {
        department: sum(1 for keyword in keywords if _contains_phrase(query, keyword))
        for department, keywords in DEPARTMENT_KEYWORDS.items()
    }


class QueryAnalyzer:
    """Analyze user queries with transparent deterministic rules."""

    def analyze(self, query: str) -> QueryAnalysis:
        """Classify intent and retrieval signals for a query."""
        stripped_query = query.strip()
        normalized = normalize_query(query)

        department_hint = self._detect_department_hint(normalized)
        detected_terms = self._detect_terms(normalized)
        intent = self._classify_intent(normalized, detected_terms)

        needs_section_lookup = any(_contains_phrase(normalized, signal) for signal in SECTION_SIGNALS)
        needs_comparison = intent == "comparison"
        needs_metadata_filter = department_hint is not None or any(
            signal in normalized for signal in METADATA_STRONG_SIGNALS
        )
        needs_exact_terms = self._needs_exact_terms(normalized, detected_terms)
        needs_semantic_search = self._needs_semantic_search(normalized, intent, needs_exact_terms)
        needs_step_by_step_answer = intent in {"procedure", "troubleshooting"}
        confidence = self._confidence(intent, department_hint, detected_terms)

        return QueryAnalysis(
            query=stripped_query,
            intent=intent,
            department_hint=department_hint,
            needs_exact_terms=needs_exact_terms,
            needs_semantic_search=needs_semantic_search,
            needs_metadata_filter=needs_metadata_filter,
            needs_section_lookup=needs_section_lookup,
            needs_comparison=needs_comparison,
            needs_step_by_step_answer=needs_step_by_step_answer,
            detected_terms=detected_terms,
            confidence=confidence,
        )

    def _classify_intent(self, query: str, detected_terms: list[str]) -> str:
        if not query or query in {"help", "hi", "hello"}:
            return "ambiguous"

        matched: set[str] = set()
        for intent, signals in INTENT_SIGNALS.items():
            if any(_contains_phrase(query, signal) for signal in signals):
                matched.add(intent)

        if self._needs_exact_terms(query, detected_terms):
            matched.add("exact_lookup")

        # Prefer procedural wording over a bare exact phrase like "rollback procedure".
        if "exact_lookup" in matched and "procedure" in matched:
            procedural_question = any(
                signal in query for signal in ("how do", "how should", "what should", "steps", "step")
            )
            if not procedural_question and query in {"rollback procedure", "deployment guide"}:
                matched.discard("procedure")

        for intent in INTENT_PRIORITY:
            if intent in matched:
                return intent
        return "ambiguous"

    def _detect_department_hint(self, query: str) -> str | None:
        counts = _count_department_matches(query)
        best_count = max(counts.values(), default=0)
        if best_count == 0:
            return None
        winners = [department for department, count in counts.items() if count == best_count]
        return winners[0] if len(winners) == 1 else None

    def _detect_terms(self, query: str) -> list[str]:
        found: list[tuple[int, str]] = []
        seen: set[str] = set()
        for term in IMPORTANT_TERMS:
            match = re.search(rf"\b{re.escape(term)}\b", query)
            if match and term not in seen:
                found.append((match.start(), term.upper() if term in ACRONYMS else term))
                seen.add(term)
        found.sort(key=lambda item: item[0])
        return [term for _, term in found]

    def _needs_exact_terms(self, query: str, detected_terms: list[str]) -> bool:
        if detected_terms and any(term.lower() in EXACT_PHRASES or term.lower() in ACRONYMS for term in detected_terms):
            return True
        tokens = set(re.findall(r"[a-z0-9]+", query))
        if tokens.intersection(ACRONYMS | EXACT_WORDS):
            return True
        if re.search(r"\b\d+(\.\d+)?\b", query):
            return True
        return any(phrase in query for phrase in EXACT_PHRASES)

    def _needs_semantic_search(self, query: str, intent: str, needs_exact_terms: bool) -> bool:
        if any(phrase in query for phrase in SEMANTIC_PHRASES):
            return True
        if intent in {"procedure", "troubleshooting", "comparison"}:
            return True
        if query.startswith(("how ", "what should ", "can i ", "can we ")):
            return True
        token_count = len(query.split())
        if token_count >= 5 and not needs_exact_terms:
            return True
        if token_count >= 6:
            return True
        return False

    def _confidence(
        self,
        intent: str,
        department_hint: str | None,
        detected_terms: list[str],
    ) -> float:
        if intent == "ambiguous":
            return 0.4
        strong_intent = intent in set(INTENT_PRIORITY)
        if strong_intent and department_hint:
            return 0.9
        if strong_intent or detected_terms:
            return 0.75
        return 0.6
