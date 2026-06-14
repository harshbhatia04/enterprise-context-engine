from app.generation.prompt_builder import PromptBuilder
from app.schemas import Citation, ContextBuildResult
from app.security.access_control import SAFE_ABSTAIN_MESSAGE


def make_context_result(safe_abstain: bool = False) -> ContextBuildResult:
    citations = [] if safe_abstain else [
        Citation(
            source_id=1,
            chunk_id="chunk-1",
            document_id="doc-1",
            document_title="Invoice Approval Policy",
            department="finance",
            section_title="Approval Limits",
            access_level="finance",
        )
    ]
    return ContextBuildResult(
        query="What is the invoice approval limit?",
        context_text="" if safe_abstain else "[1]\nDocument: Invoice Approval Policy\nText:\nApproval details.",
        citations=citations,
        included_chunks=[],
        safe_abstain=safe_abstain,
        safe_message=SAFE_ABSTAIN_MESSAGE if safe_abstain else None,
        debug={"restricted": "debug should not appear"},
    )


def test_prompt_includes_answer_only_from_context_instruction() -> None:
    prompt = PromptBuilder().build("question", make_context_result())

    assert "Answer only using the accessible context provided." in prompt.system_prompt


def test_prompt_includes_context_text_for_authorized_context() -> None:
    prompt = PromptBuilder().build("question", make_context_result())

    assert "Invoice Approval Policy" in prompt.user_prompt
    assert prompt.context_text


def test_prompt_does_not_include_debug_fields() -> None:
    prompt = PromptBuilder().build("question", make_context_result())

    assert "restricted" not in prompt.system_prompt
    assert "restricted" not in prompt.user_prompt


def test_safe_abstain_prompt_contains_no_context() -> None:
    prompt = PromptBuilder().build("question", make_context_result(safe_abstain=True))

    assert prompt.safe_abstain is True
    assert prompt.context_text == ""
    context_part = prompt.user_prompt.split("Accessible context:", 1)[-1].split("Instructions:", 1)[0]
    assert context_part.strip() == ""


def test_prompt_citation_count_is_correct() -> None:
    assert PromptBuilder().build("question", make_context_result()).citation_count == 1
    assert PromptBuilder().build("question", make_context_result(safe_abstain=True)).citation_count == 0
