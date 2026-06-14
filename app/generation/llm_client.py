"""LLM clients for answer generation."""

from __future__ import annotations

import os
import re
from abc import ABC, abstractmethod

from app.security.access_control import SAFE_ABSTAIN_MESSAGE


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

        source_blocks = self._extract_source_blocks(user_prompt)
        if not source_blocks:
            answer = SAFE_ABSTAIN_MESSAGE
            return answer, self._usage(system_prompt, user_prompt, answer)

        first_id, first_text = source_blocks[0]
        first_sentence = self._first_useful_sentence(first_text)
        if len(source_blocks) > 1:
            second_id, second_text = source_blocks[1]
            second_sentence = self._first_useful_sentence(second_text)
            answer = (
                f"Based on the accessible context, {first_sentence} [{first_id}]. "
                f"Additional relevant guidance says {second_sentence} [{second_id}]."
            )
        else:
            answer = f"Based on the accessible context, {first_sentence} [{first_id}]."
        return answer, self._usage(system_prompt, user_prompt, answer)

    @staticmethod
    def _has_no_context(user_prompt: str) -> bool:
        context = user_prompt.split("Accessible context:", 1)[-1].split("Instructions:", 1)[0].strip()
        return not context or SAFE_ABSTAIN_MESSAGE in context

    @staticmethod
    def _extract_source_blocks(user_prompt: str) -> list[tuple[int, str]]:
        context = user_prompt.split("Accessible context:", 1)[-1].split("Instructions:", 1)[0]
        matches = list(re.finditer(r"^\[(\d+)\]\s*$", context, flags=re.MULTILINE))
        blocks: list[tuple[int, str]] = []
        for index, match in enumerate(matches):
            source_id = int(match.group(1))
            start = match.end()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(context)
            blocks.append((source_id, context[start:end].strip()))
        return blocks

    @staticmethod
    def _first_useful_sentence(block: str) -> str:
        text = block.split("Text:", 1)[-1] if "Text:" in block else block
        cleaned_lines = []
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("#"):
                continue
            cleaned_lines.append(stripped.lstrip("-* ").strip())
        cleaned = " ".join(cleaned_lines)
        if not cleaned:
            return "the cited source contains the relevant guidance"
        sentence_match = re.match(r"(.+?[.!?])(?:\s|$)", cleaned)
        return sentence_match.group(1).strip() if sentence_match else cleaned

    @staticmethod
    def _usage(system_prompt: str, user_prompt: str, answer: str) -> dict[str, int]:
        prompt_tokens = len(system_prompt.split()) + len(user_prompt.split())
        completion_tokens = len(answer.split())
        return {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        }


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
