"""Progressive disclosure for candidate discovery and focused chunk retrieval."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from app.context_engine.query_analyzer import normalize_query
from app.context_engine.retrieval_router import RetrievalRouter
from app.retrieval.bm25_retriever import BM25Retriever, tokenize
from app.retrieval.dense_retriever import DenseRetriever, FakeEmbeddingModel
from app.retrieval.hybrid_retriever import HybridRetriever
from app.security.access_control import AccessController
from app.schemas import (
    CandidateDocument,
    CandidateSection,
    Chunk,
    ProgressiveDisclosureResult,
    RetrievalPlan,
    RetrievalResult,
    SecureProgressiveDisclosureResult,
)


class ProgressiveDisclosureEngine:
    """Discover candidate documents/sections before fetching focused chunks."""

    def __init__(
        self,
        bm25_retriever: BM25Retriever | None = None,
        dense_retriever: DenseRetriever | None = None,
        hybrid_retriever: HybridRetriever | None = None,
        router: RetrievalRouter | None = None,
    ) -> None:
        self.bm25_retriever = bm25_retriever
        self.dense_retriever = dense_retriever
        self.hybrid_retriever = hybrid_retriever
        self.router = router or RetrievalRouter()
        self.chunks: list[Chunk] = self._infer_chunks()

    def run(
        self,
        query: str,
        chunks: list[Chunk] | None = None,
        top_k: int | None = None,
    ) -> ProgressiveDisclosureResult:
        """Run retrieval planning, candidate discovery, and focused fetch."""
        if chunks is not None:
            self.chunks = list(chunks)
        self._ensure_retrievers()

        plan = self.router.build_plan(query)
        if top_k is not None:
            plan = replace(plan, top_k=top_k)

        initial_results, used_retrievers = self._initial_retrieval(plan)
        candidate_documents = self._discover_candidate_documents(initial_results, plan)
        candidate_sections = self._discover_candidate_sections(initial_results, plan)
        focused_chunks = self._fetch_focused_chunks(
            initial_results,
            candidate_documents,
            candidate_sections,
            plan.top_k,
            plan.retrieval_mode,
        )

        debug = {
            "retrieval_mode": plan.retrieval_mode,
            "intent": plan.analysis.intent,
            "candidate_document_count": len(candidate_documents),
            "candidate_section_count": len(candidate_sections),
            "focused_chunk_count": len(focused_chunks),
            "candidate_k": plan.candidate_k,
            "top_k": plan.top_k,
            "filters": plan.filters,
            "progressive_disclosure": True,
            "initial_result_count": len(initial_results),
            "used_retrievers": used_retrievers,
        }

        return ProgressiveDisclosureResult(
            query=query.strip(),
            retrieval_plan=plan,
            candidate_documents=candidate_documents,
            candidate_sections=candidate_sections,
            focused_chunks=focused_chunks,
            debug=debug,
        )

    def _ensure_retrievers(self) -> None:
        if self.chunks and self.bm25_retriever is None:
            self.bm25_retriever = BM25Retriever()
            self.bm25_retriever.build_index(self.chunks)
        if self.chunks and self.dense_retriever is None:
            self.dense_retriever = DenseRetriever(FakeEmbeddingModel())
            self.dense_retriever.build_index(self.chunks)
        if self.bm25_retriever is not None and self.dense_retriever is not None and self.hybrid_retriever is None:
            self.hybrid_retriever = HybridRetriever(self.bm25_retriever, self.dense_retriever)
        if not self.chunks:
            self.chunks = self._infer_chunks()

    def _infer_chunks(self) -> list[Chunk]:
        if self.bm25_retriever is not None and self.bm25_retriever.chunks:
            return list(self.bm25_retriever.chunks)
        if self.dense_retriever is not None and self.dense_retriever.chunks:
            return list(self.dense_retriever.chunks)
        if self.hybrid_retriever is not None:
            bm25_chunks = self.hybrid_retriever.bm25_retriever.chunks
            if bm25_chunks:
                return list(bm25_chunks)
            dense_chunks = self.hybrid_retriever.dense_retriever.chunks
            if dense_chunks:
                return list(dense_chunks)
        return []

    def _initial_retrieval(self, plan: RetrievalPlan) -> tuple[list[RetrievalResult], list[str]]:
        mode = plan.retrieval_mode
        if mode == "bm25_only":
            self._require(self.bm25_retriever, "BM25 retriever")
            return self.bm25_retriever.search(plan.query, top_k=plan.candidate_k), ["bm25"]
        if mode == "dense_only":
            self._require(self.dense_retriever, "Dense retriever")
            return self.dense_retriever.search(plan.query, top_k=plan.candidate_k), ["dense"]
        if mode == "hybrid":
            self._require(self.hybrid_retriever, "Hybrid retriever")
            return (
                self.hybrid_retriever.search(
                    plan.query,
                    top_k=plan.candidate_k,
                    candidate_k=plan.candidate_k,
                ),
                ["bm25", "dense", "hybrid"],
            )
        if mode == "metadata_lookup":
            return self._metadata_lookup(plan), ["metadata_lookup"]
        if mode == "section_lookup":
            return self._section_lookup(plan), ["section_lookup"]
        return [], []

    def _metadata_lookup(self, plan: RetrievalPlan) -> list[RetrievalResult]:
        self._require_chunks()
        department = plan.filters.get("department")
        results: list[RetrievalResult] = []
        seen_documents: set[str] = set()
        for chunk in self._sorted_chunks():
            if department and chunk.department != department:
                continue
            if chunk.document_id in seen_documents:
                continue
            score = self._metadata_score(chunk, plan)
            results.append(self._result_from_chunk(chunk, score, "metadata_lookup"))
            seen_documents.add(chunk.document_id)
        results.sort(key=lambda result: (-result.score, result.document_title.lower(), result.chunk_id))
        return results[: plan.candidate_k]

    def _section_lookup(self, plan: RetrievalPlan) -> list[RetrievalResult]:
        self._require_chunks()
        scored: list[RetrievalResult] = []
        for chunk in self._sorted_chunks():
            score = self._section_score(chunk, plan)
            if score > 0.0:
                scored.append(self._result_from_chunk(chunk, score, "section_lookup"))
        if not scored:
            scored = [
                self._result_from_chunk(chunk, self._section_score(chunk, plan), "section_lookup")
                for chunk in self._sorted_chunks()
            ]
        scored.sort(key=lambda result: (-result.score, result.document_title.lower(), result.chunk_id))
        return scored[: plan.candidate_k]

    def _discover_candidate_documents(
        self,
        initial_results: list[RetrievalResult],
        plan: RetrievalPlan,
    ) -> list[CandidateDocument]:
        grouped: dict[str, dict[str, Any]] = {}
        for result in initial_results:
            entry = grouped.setdefault(
                result.document_id,
                {
                    "result": result,
                    "scores": [],
                    "sections": [],
                    "methods": [],
                },
            )
            entry["scores"].append(result.score)
            if result.section_title not in entry["sections"]:
                entry["sections"].append(result.section_title)
            if result.retrieval_method not in entry["methods"]:
                entry["methods"].append(result.retrieval_method)

        candidates: list[CandidateDocument] = []
        for document_id, entry in grouped.items():
            result = entry["result"]
            score = max(entry["scores"]) + 0.05 * len(entry["scores"])
            candidates.append(
                CandidateDocument(
                    document_id=document_id,
                    document_title=result.document_title,
                    department=result.department,
                    access_level=result.access_level,
                    score=score,
                    matched_sections=entry["sections"],
                    retrieval_methods=entry["methods"],
                    metadata=dict(result.metadata),
                )
            )
        max_documents = 8 if plan.analysis.intent == "comparison" else 5
        candidates.sort(
            key=lambda candidate: (
                -candidate.score,
                candidate.document_title.lower(),
                candidate.document_id,
            )
        )
        return candidates[:max_documents]

    def _discover_candidate_sections(
        self,
        initial_results: list[RetrievalResult],
        plan: RetrievalPlan,
    ) -> list[CandidateSection]:
        grouped: dict[tuple[str, str], dict[str, Any]] = {}
        for result in initial_results:
            key = (result.document_id, result.section_title)
            entry = grouped.setdefault(
                key,
                {
                    "result": result,
                    "score": result.score,
                    "methods": [],
                },
            )
            entry["score"] = max(entry["score"], result.score)
            if result.retrieval_method not in entry["methods"]:
                entry["methods"].append(result.retrieval_method)

        sections: list[CandidateSection] = []
        for (document_id, section_title), entry in grouped.items():
            result = entry["result"]
            sections.append(
                CandidateSection(
                    document_id=document_id,
                    document_title=result.document_title,
                    section_title=section_title,
                    department=result.department,
                    access_level=result.access_level,
                    score=entry["score"],
                    retrieval_methods=entry["methods"],
                    metadata=dict(result.metadata),
                )
            )
        max_sections = 12 if plan.analysis.intent == "comparison" else 8
        sections.sort(
            key=lambda section: (
                -section.score,
                section.document_title.lower(),
                section.section_title.lower(),
            )
        )
        return sections[:max_sections]

    def _fetch_focused_chunks(
        self,
        initial_results: list[RetrievalResult],
        candidate_documents: list[CandidateDocument],
        candidate_sections: list[CandidateSection],
        top_k: int,
        retrieval_mode: str,
    ) -> list[RetrievalResult]:
        if top_k <= 0:
            return []

        initial_by_id = {result.chunk_id: result for result in initial_results}
        candidate_section_keys = {
            (section.document_id, section.section_title) for section in candidate_sections
        }
        candidate_document_ids = {document.document_id for document in candidate_documents}
        section_scores = {
            (section.document_id, section.section_title): section.score for section in candidate_sections
        }
        document_scores = {document.document_id: document.score for document in candidate_documents}

        selected: dict[str, RetrievalResult] = {}

        def add(result: RetrievalResult) -> None:
            if result.chunk_id not in selected:
                selected[result.chunk_id] = result

        for result in self._sort_results(initial_results):
            if (result.document_id, result.section_title) in candidate_section_keys:
                add(result)

        if len(selected) < top_k:
            for chunk in self._sorted_chunks():
                key = (chunk.document_id, chunk.section_title)
                if key in candidate_section_keys:
                    fallback = initial_by_id.get(chunk.chunk_id) or self._result_from_chunk(
                        chunk,
                        section_scores.get(key, 0.0) * 0.95,
                        retrieval_mode,
                    )
                    add(fallback)
                if len(selected) >= top_k:
                    break

        if len(selected) < top_k:
            for result in self._sort_results(initial_results):
                if result.document_id in candidate_document_ids:
                    add(result)

        if len(selected) < top_k:
            for chunk in self._sorted_chunks():
                if chunk.document_id in candidate_document_ids:
                    fallback = initial_by_id.get(chunk.chunk_id) or self._result_from_chunk(
                        chunk,
                        document_scores.get(chunk.document_id, 0.0) * 0.9,
                        retrieval_mode,
                    )
                    add(fallback)
                if len(selected) >= top_k:
                    break

        focused = list(selected.values())
        focused.sort(key=lambda result: (-result.score, result.document_title.lower(), result.chunk_id))
        return focused[:top_k]

    def _metadata_score(self, chunk: Chunk, plan: RetrievalPlan) -> float:
        score = 1.0
        if plan.filters.get("department") == chunk.department:
            score += 3.0
        query = normalize_query(plan.query)
        if chunk.document_type and chunk.document_type in query:
            score += 1.0
        if "policy" in query and chunk.document_type == "policy":
            score += 1.0
        if "version" in query or "latest" in query or "effective date" in query:
            score += 0.5
        return score

    def _section_score(self, chunk: Chunk, plan: RetrievalPlan) -> float:
        query = normalize_query(plan.query)
        query_tokens = set(tokenize(query))
        detected_terms = [term.lower() for term in plan.analysis.detected_terms]
        title = normalize_query(chunk.document_title)
        section = normalize_query(chunk.section_title)
        text = normalize_query(chunk.text)

        score = 0.0
        for term in detected_terms:
            if term in section:
                score += 4.0
            if term in title:
                score += 3.0
            if term in text:
                score += 1.0

        section_tokens = set(tokenize(section))
        title_tokens = set(tokenize(title))
        text_tokens = set(tokenize(text))
        score += 1.5 * len(query_tokens.intersection(section_tokens))
        score += 1.0 * len(query_tokens.intersection(title_tokens))
        score += 0.25 * len(query_tokens.intersection(text_tokens))
        if plan.filters.get("department") == chunk.department:
            score += 0.5
        return score

    @staticmethod
    def _result_from_chunk(chunk: Chunk, score: float, retrieval_method: str) -> RetrievalResult:
        return RetrievalResult(
            chunk_id=chunk.chunk_id,
            document_id=chunk.document_id,
            document_title=chunk.document_title,
            department=chunk.department,
            access_level=chunk.access_level,
            section_title=chunk.section_title,
            text=chunk.text,
            score=score,
            retrieval_method=retrieval_method,
            metadata={
                "document_type": chunk.document_type,
                "version": chunk.version,
                "effective_date": chunk.effective_date,
                "source_path": chunk.source_path,
                "word_count": chunk.word_count,
            },
        )

    def _sorted_chunks(self) -> list[Chunk]:
        return sorted(
            self.chunks,
            key=lambda chunk: (
                chunk.document_title.lower(),
                chunk.section_title.lower(),
                chunk.chunk_id,
            ),
        )

    @staticmethod
    def _sort_results(results: list[RetrievalResult]) -> list[RetrievalResult]:
        return sorted(
            results,
            key=lambda result: (-result.score, result.document_title.lower(), result.chunk_id),
        )

    def _require_chunks(self) -> None:
        if not self.chunks:
            raise RuntimeError("Progressive disclosure needs chunks for local metadata/section lookup.")

    @staticmethod
    def _require(value: Any, name: str) -> None:
        if value is None:
            raise RuntimeError(f"{name} is required for this retrieval mode.")


class SecureProgressiveDisclosureEngine:
    """Run progressive disclosure and filter all public context by permissions."""

    def __init__(
        self,
        progressive_engine: ProgressiveDisclosureEngine | None = None,
        access_controller: AccessController | None = None,
    ) -> None:
        self.progressive_engine = progressive_engine or ProgressiveDisclosureEngine()
        self.access_controller = access_controller or AccessController()

    def run(
        self,
        query: str,
        user_id: str,
        chunks: list[Chunk] | None = None,
        top_k: int | None = None,
    ) -> SecureProgressiveDisclosureResult:
        """Return only context the user is allowed to see."""
        base_result = self.progressive_engine.run(query, chunks=chunks, top_k=top_k)
        access_result = self.access_controller.filter_progressive_result(user_id, base_result)

        if access_result.safe_abstain:
            candidate_documents: list[CandidateDocument] = []
            candidate_sections: list[CandidateSection] = []
            focused_chunks: list[RetrievalResult] = []
        else:
            candidate_documents = access_result.accessible_candidate_documents
            candidate_sections = access_result.accessible_candidate_sections
            focused_chunks = access_result.accessible_focused_chunks

        debug = {
            **access_result.debug,
            "retrieval_mode": base_result.retrieval_plan.retrieval_mode,
            "intent": base_result.retrieval_plan.analysis.intent,
            "safe_abstain": access_result.safe_abstain,
        }

        return SecureProgressiveDisclosureResult(
            query=query.strip(),
            user_id=user_id,
            base_result=None,
            access_filter_result=access_result,
            focused_chunks=focused_chunks,
            candidate_documents=candidate_documents,
            candidate_sections=candidate_sections,
            safe_abstain=access_result.safe_abstain,
            safe_message=access_result.safe_message,
            debug=debug,
        )
