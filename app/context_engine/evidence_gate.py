"""Deterministic confidence gate for no-evidence abstention."""

from __future__ import annotations

import re
from statistics import mean

from app.schemas import ContextBuildResult, EvidenceGateDecision


STOPWORDS = {
    "what",
    "is",
    "the",
    "a",
    "an",
    "of",
    "for",
    "to",
    "do",
    "does",
    "about",
    "how",
    "we",
    "i",
    "in",
    "on",
    "and",
    "or",
    "are",
    "should",
    "company",
    "handbook",
    "policy",
    "s",
    "say",
    "says",
}

GENERIC_TERMS = {
    "company",
    "handbook",
    "policy",
    "document",
    "documents",
    "rule",
    "rules",
    "process",
    "procedure",
    "procedures",
    "plan",
    "plans",
}

TERM_ALIASES = {
    "bad": {"incident", "rollback", "production", "mitigation"},
    "back": {"reimbursement", "reimburse", "expense", "expenses"},
    "cost": {"expense", "expenses", "reimbursement"},
    "costs": {"expense", "expenses", "reimbursement"},
    "distributed": {"remote", "asynchronous", "async"},
    "handled": {"management", "response", "mitigation", "process"},
    "member": {"onboarding", "team", "members"},
    "members": {"onboarding", "team", "member"},
    "new": {"onboarding"},
    "obligations": {"obligation", "data", "protection", "privacy", "compliance"},
    "paid": {"reimbursement", "reimburse", "expense", "expenses", "repay", "repaid"},
    "release": {"rollback", "deployment", "production"},
    "restore": {"rollback", "deployment", "production"},
    "start": {"onboarding"},
    "teams": {"team"},
    "travel": {"expense", "expenses", "reimbursement"},
    "triaged": {"triage", "alerts", "security"},
    "updates": {"update", "communication"},
}


class EvidenceGate:
    """Decide whether accessible context is strong enough for generation."""

    def __init__(
        self,
        min_confidence: float = 0.25,
        min_query_term_overlap: float = 0.20,
        min_strong_signals: int = 1,
    ) -> None:
        self.min_confidence = min_confidence
        self.min_query_term_overlap = min_query_term_overlap
        self.min_strong_signals = min_strong_signals

    def evaluate(
        self,
        query: str,
        context_result: ContextBuildResult,
    ) -> EvidenceGateDecision:
        """Return a deterministic support decision for context and citations."""
        immediate_reason = self._immediate_unsupported_reason(context_result)
        if immediate_reason:
            return EvidenceGateDecision(
                is_supported=False,
                confidence_score=0.0,
                reason=immediate_reason,
                debug={
                    "matched_terms": [],
                    "missing_terms": [],
                    "important_query_terms": [],
                    "term_overlap": 0.0,
                    "citation_signal": 0.0,
                    "score_signal": 0.0,
                    "title_signal": 0.0,
                    "strong_signal_count": 0,
                },
            )

        important_terms = self._important_query_terms(query)
        if not important_terms:
            return EvidenceGateDecision(
                is_supported=False,
                confidence_score=0.0,
                reason="query contains no specific evidence terms",
                debug={
                    "matched_terms": [],
                    "missing_terms": [],
                    "important_query_terms": [],
                    "term_overlap": 0.0,
                    "citation_signal": 1.0,
                    "score_signal": self._score_signal(context_result),
                    "title_signal": 0.0,
                    "strong_signal_count": 0,
                },
            )

        evidence_tokens = self._evidence_tokens(context_result)
        title_tokens = self._title_tokens(context_result)
        matched_terms = [
            term for term in important_terms if self._term_matches(term, evidence_tokens)
        ]
        missing_terms = [term for term in important_terms if term not in matched_terms]
        matched_title_terms = [
            term for term in important_terms if self._term_matches(term, title_tokens)
        ]

        term_overlap = len(matched_terms) / len(important_terms)
        citation_signal = 1.0 if context_result.citations else 0.0
        score_signal = self._score_signal(context_result)
        title_signal = 1.0 if matched_title_terms else 0.0
        confidence_score = self._clamp(
            (0.45 * term_overlap)
            + (0.20 * citation_signal)
            + (0.20 * score_signal)
            + (0.15 * title_signal)
        )
        strong_signal_count = sum(
            [
                term_overlap >= self.min_query_term_overlap,
                title_signal > 0,
                score_signal >= 0.55,
            ]
        )
        has_specific_overlap = bool(matched_terms)
        is_supported = (
            has_specific_overlap
            and confidence_score >= self.min_confidence
            and strong_signal_count >= self.min_strong_signals
        )
        reason = (
            "accessible context has enough lexical and citation support"
            if is_supported
            else "accessible context is too weak or unrelated to answer"
        )

        return EvidenceGateDecision(
            is_supported=is_supported,
            confidence_score=confidence_score,
            reason=reason,
            matched_terms=matched_terms,
            missing_terms=missing_terms,
            debug={
                "matched_terms": matched_terms,
                "missing_terms": missing_terms,
                "important_query_terms": important_terms,
                "matched_title_terms": matched_title_terms,
                "term_overlap": term_overlap,
                "citation_signal": citation_signal,
                "score_signal": score_signal,
                "title_signal": title_signal,
                "strong_signal_count": strong_signal_count,
                "min_confidence": self.min_confidence,
                "min_query_term_overlap": self.min_query_term_overlap,
                "min_strong_signals": self.min_strong_signals,
            },
        )

    @staticmethod
    def _immediate_unsupported_reason(context_result: ContextBuildResult) -> str | None:
        if context_result.safe_abstain:
            return "context builder already safe-abstained"
        if not context_result.context_text.strip():
            return "context text is empty"
        if not context_result.citations:
            return "context has no citations"
        if not context_result.included_chunks:
            return "context has no included chunks"
        return None

    @classmethod
    def _important_query_terms(cls, query: str) -> list[str]:
        terms: list[str] = []
        seen: set[str] = set()
        for token in cls._tokenize(query):
            if token in STOPWORDS or token in GENERIC_TERMS:
                continue
            if token not in seen:
                seen.add(token)
                terms.append(token)
        return terms

    @classmethod
    def _evidence_tokens(cls, context_result: ContextBuildResult) -> set[str]:
        fields = [context_result.context_text]
        for citation in context_result.citations:
            fields.extend([citation.document_title, citation.section_title])
        for chunk in context_result.included_chunks:
            fields.extend([chunk.document_title, chunk.section_title, chunk.text])
        return cls._token_set(" ".join(fields))

    @classmethod
    def _title_tokens(cls, context_result: ContextBuildResult) -> set[str]:
        fields: list[str] = []
        for citation in context_result.citations:
            fields.extend([citation.document_title, citation.section_title])
        for chunk in context_result.included_chunks:
            fields.extend([chunk.document_title, chunk.section_title])
        return cls._token_set(" ".join(fields))

    @classmethod
    def _token_set(cls, text: str) -> set[str]:
        tokens = set(cls._tokenize(text))
        expanded = set(tokens)
        for token in tokens:
            expanded.update(cls._variants(token))
        return expanded

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return [token for token in re.split(r"[^a-z0-9]+", text.lower()) if token]

    @classmethod
    def _term_matches(cls, term: str, evidence_tokens: set[str]) -> bool:
        return bool((cls._variants(term) | TERM_ALIASES.get(term, set())) & evidence_tokens)

    @staticmethod
    def _variants(token: str) -> set[str]:
        variants = {token}
        if len(token) > 4 and token.endswith("ies"):
            variants.add(token[:-3] + "y")
        if len(token) > 3 and token.endswith("es"):
            variants.add(token[:-2])
        if len(token) > 3 and token.endswith("s"):
            variants.add(token[:-1])
        return variants

    @staticmethod
    def _score_signal(context_result: ContextBuildResult) -> float:
        scores = [
            EvidenceGate._clamp(chunk.final_score)
            for chunk in context_result.included_chunks
            if chunk.final_score is not None
        ]
        if not scores:
            return 0.5
        return mean(scores)

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(1.0, float(value)))
