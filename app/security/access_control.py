"""Permission-aware filtering for retrieved enterprise context."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.schemas import (
    AccessDecision,
    AccessFilterResult,
    CandidateDocument,
    CandidateSection,
    Chunk,
    ProgressiveDisclosureResult,
    RetrievalResult,
)
from app.security.users import USERS

SAFE_ABSTAIN_MESSAGE = "I could not find accessible documents that support an answer to this question."

ACCESS_LEVEL_ORDER = ["all", "hr", "finance", "engineering", "legal", "public", "general"]
ADMIN_LEVELS = ACCESS_LEVEL_ORDER
DEPARTMENT_LEVELS = {"hr", "finance", "engineering", "legal"}
PUBLIC_LEVELS = {"public", "general"}


class AccessController:
    """Apply user permissions to retrieval candidates and focused chunks."""

    def __init__(self, users: dict[str, dict[str, Any]] | None = None) -> None:
        self.users = deepcopy(users if users is not None else USERS)

    def get_user(self, user_id: str) -> dict[str, Any]:
        """Return a configured user or raise a clear error."""
        if user_id not in self.users:
            raise ValueError(f"Unknown user_id: {user_id}")
        return deepcopy(self.users[user_id])

    def get_allowed_access_levels(self, user_id: str) -> list[str]:
        """Return effective access levels for a user."""
        user = self.get_user(user_id)
        role = str(user.get("role", "")).lower()
        configured_levels = {
            str(level).lower() for level in user.get("access_levels", []) if str(level).strip()
        }
        department = str(user.get("department", "")).lower()

        if role == "admin" or "all" in configured_levels:
            return list(ADMIN_LEVELS)
        if department in DEPARTMENT_LEVELS:
            allowed = {department, *PUBLIC_LEVELS}
        else:
            allowed = set(PUBLIC_LEVELS)
        allowed.update(level for level in configured_levels if level in PUBLIC_LEVELS)
        return [level for level in ACCESS_LEVEL_ORDER if level in allowed]

    def decide_access_level(self, user_id: str, access_level: str) -> AccessDecision:
        """Return a structured access decision for one access level."""
        allowed_levels = self.get_allowed_access_levels(user_id)
        normalized_level = self._normalize_access_level(access_level)
        allowed = "all" in allowed_levels or normalized_level in allowed_levels
        reason = "allowed" if allowed else "access level is not permitted for this user"
        return AccessDecision(
            user_id=user_id,
            allowed=allowed,
            reason=reason,
            allowed_access_levels=allowed_levels,
        )

    def can_access_level(self, user_id: str, access_level: str) -> bool:
        """Check whether a user can access a metadata access level."""
        return self.decide_access_level(user_id, access_level).allowed

    def can_access_chunk(self, user_id: str, chunk: RetrievalResult | Chunk) -> bool:
        """Check whether a user can access a retrieved chunk."""
        return self.can_access_level(user_id, chunk.access_level)

    def can_access_candidate_document(self, user_id: str, doc: CandidateDocument) -> bool:
        """Check whether a user can access a candidate document."""
        return self.can_access_level(user_id, doc.access_level)

    def can_access_candidate_section(self, user_id: str, section: CandidateSection) -> bool:
        """Check whether a user can access a candidate section."""
        return self.can_access_level(user_id, section.access_level)

    def filter_progressive_result(
        self,
        user_id: str,
        result: ProgressiveDisclosureResult,
    ) -> AccessFilterResult:
        """Filter a progressive disclosure result without leaking restricted details."""
        allowed_levels = self.get_allowed_access_levels(user_id)
        accessible_documents = [
            doc
            for doc in result.candidate_documents
            if self.can_access_candidate_document(user_id, doc)
        ]
        accessible_sections = [
            section
            for section in result.candidate_sections
            if self.can_access_candidate_section(user_id, section)
        ]
        accessible_chunks = [
            chunk for chunk in result.focused_chunks if self.can_access_chunk(user_id, chunk)
        ]

        safe_abstain = len(accessible_chunks) == 0
        if safe_abstain:
            accessible_documents = []
            accessible_sections = []

        filtered_document_count = len(result.candidate_documents) - len(accessible_documents)
        filtered_section_count = len(result.candidate_sections) - len(accessible_sections)
        filtered_chunk_count = len(result.focused_chunks) - len(accessible_chunks)

        debug = {
            "user_id": user_id,
            "allowed_access_levels": allowed_levels,
            "candidate_documents_before": len(result.candidate_documents),
            "candidate_documents_after": len(accessible_documents),
            "candidate_sections_before": len(result.candidate_sections),
            "candidate_sections_after": len(accessible_sections),
            "focused_chunks_before": len(result.focused_chunks),
            "focused_chunks_after": len(accessible_chunks),
            "filtered_document_count": filtered_document_count,
            "filtered_section_count": filtered_section_count,
            "filtered_chunk_count": filtered_chunk_count,
        }

        return AccessFilterResult(
            user_id=user_id,
            accessible_candidate_documents=accessible_documents,
            accessible_candidate_sections=accessible_sections,
            accessible_focused_chunks=accessible_chunks,
            filtered_document_count=filtered_document_count,
            filtered_section_count=filtered_section_count,
            filtered_chunk_count=filtered_chunk_count,
            safe_abstain=safe_abstain,
            safe_message=SAFE_ABSTAIN_MESSAGE if safe_abstain else None,
            debug=debug,
        )

    @staticmethod
    def _normalize_access_level(access_level: str) -> str:
        return str(access_level or "").strip().lower()
