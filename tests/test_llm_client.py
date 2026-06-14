from app.generation.llm_client import MockLLMClient
from app.security.access_control import SAFE_ABSTAIN_MESSAGE


SYSTEM_PROMPT = "system"
NORMAL_USER_PROMPT = """User question:
What is the invoice approval limit?

Accessible context:
[1]
Document: Invoice Approval Policy
Text:
Teams should capture approval evidence before work proceeds.

Instructions:
- Answer only from the accessible context.
"""


def test_mock_llm_requires_no_api_key() -> None:
    client = MockLLMClient()

    assert client.model_name == "mock-llm"


def test_mock_llm_safe_abstention_returns_exact_message() -> None:
    user_prompt = """User question:
secret?

Accessible context:

Instructions:
- If the context does not support an answer, use the safe abstention message exactly.
"""

    answer, _ = MockLLMClient().generate(SYSTEM_PROMPT, user_prompt)

    assert answer == SAFE_ABSTAIN_MESSAGE


def test_mock_llm_normal_context_returns_citation_marker() -> None:
    answer, _ = MockLLMClient().generate(SYSTEM_PROMPT, NORMAL_USER_PROMPT)

    assert "[1]" in answer
    assert "approval evidence" in answer


def test_mock_llm_usage_contains_token_counts() -> None:
    _, usage = MockLLMClient().generate(SYSTEM_PROMPT, NORMAL_USER_PROMPT)

    assert {"prompt_tokens", "completion_tokens", "total_tokens"}.issubset(usage)
    assert usage["total_tokens"] == usage["prompt_tokens"] + usage["completion_tokens"]


def test_mock_llm_output_is_deterministic() -> None:
    client = MockLLMClient()

    assert client.generate(SYSTEM_PROMPT, NORMAL_USER_PROMPT) == client.generate(
        SYSTEM_PROMPT,
        NORMAL_USER_PROMPT,
    )
