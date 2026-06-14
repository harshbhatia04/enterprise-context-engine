"""Grounded answer generation from secure context."""

from __future__ import annotations

import re

from app.context_engine.evidence_gate import EvidenceGate
from app.context_engine.context_builder import build_secure_context
from app.generation.llm_client import BaseLLMClient, MockLLMClient
from app.generation.prompt_builder import PromptBuilder
from app.schemas import Chunk, ContextBuildResult, EvidenceGateDecision, GeneratedAnswer
from app.security.access_control import SAFE_ABSTAIN_MESSAGE


class AnswerGenerator:
    """Generate answers from secure, citation-backed context only."""

    def __init__(
        self,
        prompt_builder: PromptBuilder | None = None,
        llm_client: BaseLLMClient | None = None,
        evidence_gate: EvidenceGate | None = None,
        use_evidence_gate: bool = True,
    ) -> None:
        self.prompt_builder = prompt_builder or PromptBuilder()
        self.llm_client = llm_client or MockLLMClient()
        self.evidence_gate = evidence_gate or EvidenceGate()
        self.use_evidence_gate = use_evidence_gate

    def generate_from_context(
        self,
        query: str,
        context_result: ContextBuildResult,
    ) -> GeneratedAnswer:
        """Generate an answer from a prebuilt secure context result."""
        if context_result.safe_abstain:
            return GeneratedAnswer(
                query=query,
                answer=context_result.safe_message or SAFE_ABSTAIN_MESSAGE,
                citations=[],
                safe_abstain=True,
                safe_message=context_result.safe_message or SAFE_ABSTAIN_MESSAGE,
                model_name=self.llm_client.model_name,
                usage={},
                debug=self._debug_base(context_result, llm_called=False, citation_count=0, context_word_count=0),
            )

        evidence_decision: EvidenceGateDecision | None = None
        if self.use_evidence_gate:
            evidence_decision = self.evidence_gate.evaluate(query, context_result)
            if not evidence_decision.is_supported:
                return GeneratedAnswer(
                    query=query,
                    answer=SAFE_ABSTAIN_MESSAGE,
                    citations=[],
                    safe_abstain=True,
                    safe_message=SAFE_ABSTAIN_MESSAGE,
                    model_name=self.llm_client.model_name,
                    usage={},
                    debug={
                        **self._debug_base(
                            context_result,
                            llm_called=False,
                            citation_count=0,
                            context_word_count=context_result.debug.get(
                                "context_word_count",
                                len(context_result.context_text.split()),
                            ),
                        ),
                        "included_chunk_count": context_result.debug.get("included_chunk_count"),
                        "evidence_gate": self._evidence_debug(evidence_decision),
                    },
                )

        prompt = self.prompt_builder.build(query, context_result)
        answer, usage = self.llm_client.generate(prompt.system_prompt, prompt.user_prompt)
        answer = self._ensure_valid_citation(answer, len(context_result.citations))
        return GeneratedAnswer(
            query=query,
            answer=answer,
            citations=context_result.citations,
            safe_abstain=False,
            safe_message=None,
            model_name=self.llm_client.model_name,
            usage=usage,
            debug={
                **self._debug_base(
                    context_result,
                    llm_called=True,
                    citation_count=len(context_result.citations),
                    context_word_count=context_result.debug.get(
                        "context_word_count",
                        len(context_result.context_text.split()),
                    ),
                ),
                "included_chunk_count": context_result.debug.get("included_chunk_count"),
                "evidence_gate": self._evidence_debug(evidence_decision) if evidence_decision else None,
            },
        )

    def generate(
        self,
        query: str,
        user_id: str,
        chunks: list[Chunk],
        top_k: int = 5,
    ) -> GeneratedAnswer:
        """Build secure context and generate an answer for one user query."""
        context_result = build_secure_context(query, user_id, chunks, top_k=top_k)
        return self.generate_from_context(query, context_result)

    @staticmethod
    def _ensure_valid_citation(answer: str, citation_count: int) -> str:
        if citation_count <= 0 or answer == SAFE_ABSTAIN_MESSAGE:
            return answer
        markers = [int(match) for match in re.findall(r"\[(\d+)\]", answer)]
        if not markers:
            return answer.rstrip() + " [1]"
        valid_markers = [marker for marker in markers if 1 <= marker <= citation_count]
        if valid_markers:
            return answer
        return re.sub(r"\[\d+\]", "[1]", answer, count=1)

    def _debug_base(
        self,
        context_result: ContextBuildResult,
        llm_called: bool,
        citation_count: int,
        context_word_count: int,
    ) -> dict:
        return {
            "llm_called": llm_called,
            "citation_count": citation_count,
            "context_word_count": context_word_count,
            "model_name": self.llm_client.model_name,
            "retrieval_mode": context_result.debug.get("retrieval_mode"),
            "intent": context_result.debug.get("intent"),
            "focused_chunks_before_access": context_result.debug.get("focused_chunks_before_access"),
            "focused_chunks_after_access": context_result.debug.get("focused_chunks_after_access"),
            "filtered_chunk_count": context_result.debug.get("filtered_chunk_count"),
        }

    @staticmethod
    def _evidence_debug(decision: EvidenceGateDecision) -> dict:
        return {
            "is_supported": decision.is_supported,
            "confidence_score": decision.confidence_score,
            "reason": decision.reason,
            "matched_terms": list(decision.matched_terms),
            "missing_terms": list(decision.missing_terms),
            "debug": dict(decision.debug),
        }
