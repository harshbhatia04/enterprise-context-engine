"""Build compact citation-backed context for downstream LLMs."""

from __future__ import annotations

from dataclasses import replace

from app.context_engine.citation_builder import CitationBuilder
from app.context_engine.progressive_disclosure import SecureProgressiveDisclosureEngine
from app.retrieval.reranker import BaseReranker, FakeReranker
from app.schemas import Chunk, ContextBuildResult, RerankedResult
from app.security.access_control import SAFE_ABSTAIN_MESSAGE


class ContextBuilder:
    """Create LLM-ready context text from reranked accessible chunks."""

    def __init__(
        self,
        max_context_words: int = 1200,
        max_chunk_words: int = 300,
    ) -> None:
        self.max_context_words = max_context_words
        self.max_chunk_words = max_chunk_words
        self.citation_builder = CitationBuilder()

    def build(
        self,
        query: str,
        chunks: list[RerankedResult],
        safe_abstain: bool = False,
        safe_message: str | None = None,
    ) -> ContextBuildResult:
        """Build context text and citations from accessible chunks."""
        if safe_abstain:
            return self._safe_result(query, safe_message or SAFE_ABSTAIN_MESSAGE, len(chunks))
        if not chunks:
            return self._safe_result(query, SAFE_ABSTAIN_MESSAGE, 0)

        deduped = self._deduplicate(chunks)
        included: list[RerankedResult] = []
        context_blocks: list[str] = []
        context_word_count = 0
        truncated_chunks = 0

        for chunk in deduped:
            truncated_text, was_truncated = self._truncate_words(chunk.text, self.max_chunk_words)
            if was_truncated:
                truncated_chunks += 1

            source_id = len(included) + 1
            block = self._format_block(source_id, chunk, truncated_text)
            block_word_count = self._word_count(block)
            if context_word_count + block_word_count > self.max_context_words:
                if included:
                    break
                remaining_text_words = max(self.max_context_words - self._metadata_word_count(chunk), 0)
                truncated_text, _ = self._truncate_words(chunk.text, remaining_text_words)
                block = self._format_block(source_id, chunk, truncated_text)
                block_word_count = self._word_count(block)
            if block_word_count == 0 or context_word_count + block_word_count > self.max_context_words:
                continue

            included.append(chunk)
            context_blocks.append(block)
            context_word_count += block_word_count

        if not included:
            return self._safe_result(query, SAFE_ABSTAIN_MESSAGE, len(chunks))

        citations = self.citation_builder.build(included)
        context_text = "\n\n".join(context_blocks)
        return ContextBuildResult(
            query=query,
            context_text=context_text,
            citations=citations,
            included_chunks=included,
            safe_abstain=False,
            safe_message=None,
            debug={
                "input_chunk_count": len(chunks),
                "included_chunk_count": len(included),
                "citation_count": len(citations),
                "max_context_words": self.max_context_words,
                "max_chunk_words": self.max_chunk_words,
                "context_word_count": self._word_count(context_text),
                "truncated_chunks": truncated_chunks,
            },
        )

    def _safe_result(
        self,
        query: str,
        safe_message: str,
        input_chunk_count: int,
    ) -> ContextBuildResult:
        return ContextBuildResult(
            query=query,
            context_text="",
            citations=[],
            included_chunks=[],
            safe_abstain=True,
            safe_message=safe_message,
            debug={
                "input_chunk_count": input_chunk_count,
                "included_chunk_count": 0,
                "citation_count": 0,
                "max_context_words": self.max_context_words,
                "max_chunk_words": self.max_chunk_words,
                "context_word_count": 0,
                "truncated_chunks": 0,
            },
        )

    def _format_block(self, source_id: int, chunk: RerankedResult, text: str) -> str:
        version = chunk.metadata.get("version")
        effective_date = chunk.metadata.get("effective_date")
        source_name = chunk.metadata.get("source_name") or self._source_name_from_path(
            chunk.metadata.get("source_path"),
        )
        lines = [
            f"[{source_id}]",
            f"Document: {chunk.document_title}",
            f"Department: {chunk.department}",
            f"Section: {chunk.section_title}",
        ]
        if source_name:
            lines.append(f"Source: {source_name}")
        if version:
            lines.append(f"Version: {version}")
        if effective_date:
            lines.append(f"Effective Date: {effective_date}")
        lines.extend(["Text:", text])
        return "\n".join(lines).strip()

    def _metadata_word_count(self, chunk: RerankedResult) -> int:
        empty_block = self._format_block(1, chunk, "")
        return self._word_count(empty_block)

    @staticmethod
    def _deduplicate(chunks: list[RerankedResult]) -> list[RerankedResult]:
        deduped: dict[str, RerankedResult] = {}
        for chunk in chunks:
            if chunk.chunk_id not in deduped:
                deduped[chunk.chunk_id] = chunk
        return list(deduped.values())

    @staticmethod
    def _truncate_words(text: str, max_words: int) -> tuple[str, bool]:
        words = text.split()
        if max_words <= 0:
            return "", bool(words)
        if len(words) <= max_words:
            return text.strip(), False
        return " ".join(words[:max_words]), True

    @staticmethod
    def _word_count(text: str) -> int:
        return len(text.split())

    @staticmethod
    def _source_name_from_path(source_path: object) -> str | None:
        normalized = str(source_path or "").replace("\\", "/").lower()
        if "gitlab_handbook" in normalized:
            return "gitlab_handbook"
        if "sample_docs" in normalized:
            return "sample_docs"
        return None


def build_secure_context(
    query: str,
    user_id: str,
    chunks: list[Chunk],
    top_k: int = 5,
    reranker: BaseReranker | None = None,
) -> ContextBuildResult:
    """Run secure retrieval, rerank accessible chunks, and build context."""
    secure_result = SecureProgressiveDisclosureEngine().run(
        query=query,
        user_id=user_id,
        chunks=chunks,
        top_k=top_k,
    )
    builder = ContextBuilder()
    secure_debug = {
        "retrieval_mode": secure_result.debug.get("retrieval_mode"),
        "intent": secure_result.debug.get("intent"),
        "safe_abstain": secure_result.safe_abstain,
        "focused_chunks_before_access": secure_result.debug.get("focused_chunks_before"),
        "focused_chunks_after_access": secure_result.debug.get("focused_chunks_after"),
        "filtered_chunk_count": secure_result.debug.get("filtered_chunk_count"),
        "candidate_documents_before_access": secure_result.debug.get("candidate_documents_before"),
        "candidate_documents_after_access": secure_result.debug.get("candidate_documents_after"),
        "candidate_sections_before_access": secure_result.debug.get("candidate_sections_before"),
        "candidate_sections_after_access": secure_result.debug.get("candidate_sections_after"),
    }
    if secure_result.safe_abstain:
        result = builder.build(
            query=query,
            chunks=[],
            safe_abstain=True,
            safe_message=secure_result.safe_message,
        )
        return replace(result, debug={**result.debug, **secure_debug})

    reranker = reranker or FakeReranker()
    reranked = reranker.rerank(query, secure_result.focused_chunks, top_k=top_k)
    result = builder.build(query=query, chunks=reranked)
    return replace(result, debug={**result.debug, **secure_debug})
