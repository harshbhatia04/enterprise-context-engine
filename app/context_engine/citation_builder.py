"""Build source citations for LLM-ready context."""

from __future__ import annotations

from app.schemas import Citation, RerankedResult


class CitationBuilder:
    """Create deterministic source IDs for included chunks."""

    def build(self, chunks: list[RerankedResult]) -> list[Citation]:
        """Build citations in the same order as reranked chunks."""
        citations: list[Citation] = []
        for source_id, chunk in enumerate(chunks, start=1):
            citations.append(
                Citation(
                    source_id=source_id,
                    chunk_id=chunk.chunk_id,
                    document_id=chunk.document_id,
                    document_title=chunk.document_title,
                    department=chunk.department,
                    section_title=chunk.section_title,
                    access_level=chunk.access_level,
                    version=chunk.metadata.get("version"),
                    effective_date=chunk.metadata.get("effective_date"),
                    retrieval_method=chunk.retrieval_method,
                    score=chunk.final_score,
                    source_name=chunk.metadata.get("source_name") or _source_name_from_path(
                        chunk.metadata.get("source_path"),
                    ),
                )
            )
        return citations


def _source_name_from_path(source_path: object) -> str | None:
    normalized = str(source_path or "").replace("\\", "/").lower()
    if "gitlab_handbook" in normalized:
        return "gitlab_handbook"
    if "sample_docs" in normalized:
        return "sample_docs"
    return None
