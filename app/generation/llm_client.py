"""LLM clients for answer generation."""

from __future__ import annotations

import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.security.access_control import SAFE_ABSTAIN_MESSAGE


@dataclass(frozen=True)
class SourceBlock:
    source_id: int
    metadata: dict[str, str]
    text: str


class BaseLLMClient(ABC):
    """Minimal interface for chat-style LLM clients."""

    model_name: str

    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str) -> tuple[str, dict]:
        """Generate an answer and return usage metadata."""


class MockLLMClient(BaseLLMClient):
    """Deterministic offline LLM used by tests and demos."""

    def __init__(self, model_name: str = "mock-llm") -> None:
        self.model_name = model_name

    def generate(self, system_prompt: str, user_prompt: str) -> tuple[str, dict]:
        """Generate a deterministic grounded answer from source blocks."""
        if self._has_no_context(user_prompt):
            answer = SAFE_ABSTAIN_MESSAGE
            return answer, self._usage(system_prompt, user_prompt, answer)

        query = self._extract_query(user_prompt)
        source_blocks = self._extract_source_blocks(user_prompt)
        if not source_blocks:
            answer = SAFE_ABSTAIN_MESSAGE
            return answer, self._usage(system_prompt, user_prompt, answer)

        informative_blocks = [block for block in source_blocks if self._has_informative_text(block)]
        source_blocks = informative_blocks or source_blocks
        first_block = source_blocks[0]
        first_sentence = self._format_sentence(first_block, query)
        first_phrase = self._source_phrase(first_block)
        if len(source_blocks) > 1:
            second_block = source_blocks[1]
            second_sentence = self._format_sentence(second_block, query)
            second_phrase = self._additional_phrase(second_block)
            answer = (
                f"{first_phrase} {first_sentence} [{first_block.source_id}]. "
                f"{second_phrase} {second_sentence} [{second_block.source_id}]."
            )
        else:
            answer = f"{first_phrase} {first_sentence} [{first_block.source_id}]."
        answer = clean_answer_text(answer)
        return answer, self._usage(system_prompt, user_prompt, answer)

    @staticmethod
    def _has_no_context(user_prompt: str) -> bool:
        context = user_prompt.split("Accessible context:", 1)[-1].split("Instructions:", 1)[0].strip()
        return not context or SAFE_ABSTAIN_MESSAGE in context

    @staticmethod
    def _extract_query(user_prompt: str) -> str:
        match = re.search(r"User question:\s*(.*?)\n\nAccessible context:", user_prompt, flags=re.DOTALL)
        return match.group(1).strip() if match else ""

    @staticmethod
    def _extract_source_blocks(user_prompt: str) -> list[SourceBlock]:
        context = user_prompt.split("Accessible context:", 1)[-1].split("Instructions:", 1)[0]
        matches = list(re.finditer(r"^\[(\d+)\]\s*$", context, flags=re.MULTILINE))
        blocks: list[SourceBlock] = []
        for index, match in enumerate(matches):
            source_id = int(match.group(1))
            start = match.end()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(context)
            block = context[start:end].strip()
            metadata, text = MockLLMClient._parse_block(block)
            blocks.append(SourceBlock(source_id=source_id, metadata=metadata, text=text))
        return blocks

    @staticmethod
    def _parse_block(block: str) -> tuple[dict[str, str], str]:
        metadata_text, text = block.split("Text:", 1) if "Text:" in block else ("", block)
        metadata: dict[str, str] = {}
        for line in metadata_text.splitlines():
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            metadata[key.strip().lower().replace(" ", "_")] = value.strip()
        return metadata, text

    @staticmethod
    def _format_sentence(block: SourceBlock, query: str) -> str:
        sentence = MockLLMClient._best_useful_sentence(block, query)
        sentence = MockLLMClient._contextualize_sentence(sentence, block, query)
        return sentence.rstrip(".!?")

    @staticmethod
    def _best_useful_sentence(block: SourceBlock, query: str) -> str:
        cleaned_lines = []
        for line in block.text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("#") or stripped.startswith("**Fixture note:**"):
                continue
            cleaned_lines.append(stripped.lstrip("-* ").strip())
        cleaned = " ".join(cleaned_lines)
        if not cleaned:
            return "the cited source contains the relevant guidance"
        sentences = [
            sentence.strip()
            for sentence in re.findall(r"[^.!?]+[.!?]?", cleaned)
            if sentence.strip()
        ]
        useful = [sentence for sentence in sentences if not MockLLMClient._is_generic_fixture_sentence(sentence)]
        if not useful:
            return "the cited source contains the relevant guidance"
        query_terms = {
            term
            for term in re.findall(r"[a-z0-9]+", query.lower())
            if len(term) > 2 and term not in {"what", "does", "the", "say", "about", "how"}
        }
        if not query_terms:
            return useful[0]
        return max(useful, key=lambda sentence: sum(term in sentence.lower() for term in query_terms))

    @staticmethod
    def _has_informative_text(block: SourceBlock) -> bool:
        sentence = MockLLMClient._best_useful_sentence(block, "")
        return sentence != "the cited source contains the relevant guidance"

    @staticmethod
    def _is_generic_fixture_sentence(sentence: str) -> bool:
        lower = sentence.lower()
        return (
            "synthetic fixture text" in lower
            or "not official gitlab content" in lower
            or "deterministic local ingestion tests" in lower
            or "this fixture represents" in lower
        )

    @staticmethod
    def _contextualize_sentence(sentence: str, block: SourceBlock, query: str) -> str:
        cleaned = clean_answer_text(sentence)
        lower_query = query.lower()
        if block.metadata.get("source") == "gitlab_handbook" and "remote work" in lower_query:
            if "remote work" not in cleaned.lower():
                return f"for remote work, {cleaned[:1].lower()}{cleaned[1:]}"
        return MockLLMClient._rewrite_generic_policy_sentence(cleaned)

    @staticmethod
    def _rewrite_generic_policy_sentence(sentence: str) -> str:
        match = re.match(
            r"This document defines how the (?P<department>[A-Za-z]+) team applies the "
            r"(?P<topic>.+?) in daily operations\.?$",
            sentence,
        )
        if not match:
            return sentence
        department = match.group("department").upper() if match.group("department").lower() == "hr" else match.group("department")
        topic = match.group("topic")
        return f"the {department} team applies the {topic} in daily operations"

    @staticmethod
    def _source_phrase(block: SourceBlock) -> str:
        if block.metadata.get("source") == "gitlab_handbook":
            return "The handbook-style guidance says"
        document = f"{block.metadata.get('document', '')} {block.metadata.get('document_type', '')}".lower()
        if "procedure" in document:
            return "The accessible procedure says"
        return "The accessible policy states"

    @staticmethod
    def _additional_phrase(block: SourceBlock) -> str:
        if block.metadata.get("source") == "gitlab_handbook":
            return "Related handbook-style guidance adds"
        document = f"{block.metadata.get('document', '')} {block.metadata.get('document_type', '')}".lower()
        if "procedure" in document:
            return "The accessible procedure also says"
        return "The accessible policy also states"

    @staticmethod
    def _usage(system_prompt: str, user_prompt: str, answer: str) -> dict[str, int]:
        prompt_tokens = len(system_prompt.split()) + len(user_prompt.split())
        completion_tokens = len(answer.split())
        return {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        }


def clean_answer_text(text: str) -> str:
    """Clean deterministic formatting artifacts without changing citations."""
    cleaned = text
    replacements = {
        "Hr team": "HR team",
        "hr department": "HR department",
        "d aily": "daily",
        "ap proval": "approval",
        "ex pected": "expected",
    }
    for old, new in replacements.items():
        cleaned = cleaned.replace(old, new)
    cleaned = re.sub(r"\s+([.,;:!?])", r"\1", cleaned)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    return cleaned.strip()


class OpenAICompatibleLLMClient(BaseLLMClient):
    """Optional OpenAI-compatible chat client loaded only when used."""

    def __init__(
        self,
        model_name: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self.model_name = model_name or os.getenv("OPENAI_MODEL") or "gpt-4.1-mini"
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL") or None
        self._client = None

    def _load_client(self):
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is required for OpenAI-compatible generation.")
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError as exc:  # pragma: no cover - optional dependency path.
                raise RuntimeError("The openai package is required for OpenAICompatibleLLMClient.") from exc

            kwargs = {"api_key": self.api_key}
            if self.base_url:
                kwargs["base_url"] = self.base_url
            self._client = OpenAI(**kwargs)
        return self._client

    def generate(self, system_prompt: str, user_prompt: str) -> tuple[str, dict]:
        """Generate with an OpenAI-compatible chat completion API."""
        client = self._load_client()
        response = client.chat.completions.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
        )
        answer = response.choices[0].message.content or ""
        usage_obj = getattr(response, "usage", None)
        usage = {}
        if usage_obj is not None:
            usage = {
                "prompt_tokens": getattr(usage_obj, "prompt_tokens", 0),
                "completion_tokens": getattr(usage_obj, "completion_tokens", 0),
                "total_tokens": getattr(usage_obj, "total_tokens", 0),
            }
        return answer, usage
