"""Prompt construction for grounded answer generation."""

from __future__ import annotations

from app.schemas import ContextBuildResult, PromptBuildResult
from app.security.access_control import SAFE_ABSTAIN_MESSAGE

SYSTEM_PROMPT = """You are an enterprise knowledge assistant.

Answer only using the accessible context provided.
Do not use outside knowledge.
Do not invent policies, limits, dates, procedures, or document names.
Cite every factual claim using source numbers like [1] or [2].
If the accessible context is insufficient, say exactly:
"I could not find accessible documents that support an answer to this question."
Do not mention inaccessible or filtered documents.
Keep the answer concise, operational, and professional."""


class PromptBuilder:
    """Build prompts from final secure context only."""

    def build(self, query: str, context_result: ContextBuildResult) -> PromptBuildResult:
        """Build system/user prompts for grounded generation."""
        safe_message = context_result.safe_message or SAFE_ABSTAIN_MESSAGE
        context_text = "" if context_result.safe_abstain else context_result.context_text
        user_prompt = self._build_user_prompt(query, context_text)

        return PromptBuildResult(
            query=query,
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            context_text=context_text,
            citation_count=len(context_result.citations),
            safe_abstain=context_result.safe_abstain,
            safe_message=safe_message if context_result.safe_abstain else None,
            debug={
                "citation_count": len(context_result.citations),
                "context_word_count": len(context_text.split()),
                "safe_abstain": context_result.safe_abstain,
            },
        )

    @staticmethod
    def _build_user_prompt(query: str, context_text: str) -> str:
        return (
            f"User question:\n{query}\n\n"
            f"Accessible context:\n{context_text}\n\n"
            "Instructions:\n"
            "- Answer only from the accessible context.\n"
            "- Use citations like [1] and [2].\n"
            f"- If the context does not support an answer, use the safe abstention message exactly: {SAFE_ABSTAIN_MESSAGE}"
        )
