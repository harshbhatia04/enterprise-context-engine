"""Rule-based retrieval routing for the context engine."""

from __future__ import annotations

from app.context_engine.query_analyzer import METADATA_STRONG_SIGNALS, QueryAnalyzer, normalize_query
from app.schemas import QueryAnalysis, RetrievalPlan


class RetrievalRouter:
    """Build retrieval plans from deterministic query analysis."""

    def __init__(self, default_top_k: int = 5, default_candidate_k: int = 20) -> None:
        self.default_top_k = default_top_k
        self.default_candidate_k = default_candidate_k
        self.analyzer = QueryAnalyzer()

    def build_plan(self, query: str, analysis: QueryAnalysis | None = None) -> RetrievalPlan:
        """Choose a retrieval mode and search budget for a query."""
        analysis = analysis or self.analyzer.analyze(query)
        normalized = normalize_query(query)
        retrieval_mode, reason = self._select_mode(normalized, analysis)
        candidate_k, top_k = self._select_limits(analysis, retrieval_mode)
        filters = {
            "intent": analysis.intent,
            "detected_terms": analysis.detected_terms,
        }
        if analysis.department_hint:
            filters["department"] = analysis.department_hint

        return RetrievalPlan(
            query=query.strip(),
            retrieval_mode=retrieval_mode,
            reason=reason,
            analysis=analysis,
            candidate_k=candidate_k,
            top_k=top_k,
            filters=filters,
        )

    def _select_mode(self, query: str, analysis: QueryAnalysis) -> tuple[str, str]:
        asks_for_metadata = any(signal in query for signal in METADATA_STRONG_SIGNALS)

        if analysis.intent == "metadata_request" or (
            analysis.needs_metadata_filter and asks_for_metadata
        ):
            return (
                "metadata_lookup",
                "Metadata lookup selected because the query asks for document/version metadata.",
            )
        if analysis.intent == "section_request" or analysis.needs_section_lookup:
            return (
                "section_lookup",
                "Section lookup selected because the query asks for a specific section or clause.",
            )
        if analysis.needs_exact_terms and not analysis.needs_semantic_search:
            return (
                "bm25_only",
                "BM25 selected because the query is an exact lookup for named policy/acronym exact terms.",
            )
        if (
            analysis.needs_semantic_search
            and not analysis.needs_exact_terms
            and analysis.department_hint is None
        ):
            return (
                "dense_only",
                "Dense retrieval selected because the query is paraphrased and has no strong exact terms.",
            )
        if analysis.needs_exact_terms and analysis.needs_semantic_search:
            return (
                "hybrid",
                "Hybrid retrieval selected because the query contains both exact policy terms and semantic wording.",
            )
        if analysis.department_hint:
            return (
                "hybrid",
                "Hybrid retrieval selected because the query has department-specific enterprise context.",
            )
        if analysis.intent in {"comparison", "troubleshooting", "procedure", "policy_question"}:
            return (
                "hybrid",
                "Hybrid retrieval selected for a normal enterprise policy or procedure question.",
            )
        return (
            "hybrid",
            "Hybrid retrieval selected as the default balanced strategy.",
        )

    def _select_limits(self, analysis: QueryAnalysis, retrieval_mode: str) -> tuple[int, int]:
        if retrieval_mode == "metadata_lookup" or analysis.intent == "metadata_request":
            return 50, 20
        if analysis.intent == "comparison":
            return 30, 8
        if analysis.intent in {"troubleshooting", "procedure"}:
            return 25, 6
        if analysis.intent == "exact_lookup" or retrieval_mode == "bm25_only":
            return 10, 5
        return self.default_candidate_k, self.default_top_k
