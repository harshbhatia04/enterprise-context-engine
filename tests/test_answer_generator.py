from app.generation.answer_generator import AnswerGenerator
from app.generation.llm_client import BaseLLMClient
from app.ingestion.pipeline import ingest_directory
from app.schemas import Citation, ContextBuildResult, RerankedResult
from app.security.access_control import SAFE_ABSTAIN_MESSAGE
from scripts.create_sample_docs import create_sample_docs


class RecordingLLMClient(BaseLLMClient):
    def __init__(self, answer: str = "Grounded answer [1]") -> None:
        self.model_name = "recording"
        self.answer = answer
        self.calls = 0

    def generate(self, system_prompt: str, user_prompt: str) -> tuple[str, dict]:
        self.calls += 1
        return self.answer, {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}


def make_context_result(safe_abstain: bool = False) -> ContextBuildResult:
    chunk = RerankedResult(
        chunk_id="chunk-1",
        document_id="doc-1",
        document_title="Invoice Approval Policy",
        department="finance",
        access_level="finance",
        section_title="Approval Limits",
        text="Invoice approval details include approval limits and exception handling.",
        original_score=0.9,
        rerank_score=0.9,
        final_score=0.9,
        retrieval_method="hybrid",
    )
    citations = (
        []
        if safe_abstain
        else [
            Citation(
                source_id=1,
                chunk_id="chunk-1",
                document_id="doc-1",
                document_title="Invoice Approval Policy",
                department="finance",
                section_title="Approval Limits",
                access_level="finance",
                score=0.9,
            )
        ]
    )
    return ContextBuildResult(
        query="What is the invoice approval limit?",
        context_text=(
            ""
            if safe_abstain
            else (
                "[1]\nDocument: Invoice Approval Policy\nSection: Approval Limits\n"
                "Text:\nInvoice approval details include approval limits and exception handling."
            )
        ),
        citations=citations,
        included_chunks=[] if safe_abstain else [chunk],
        safe_abstain=safe_abstain,
        safe_message=SAFE_ABSTAIN_MESSAGE if safe_abstain else None,
        debug={"context_word_count": 12, "included_chunk_count": 1 if not safe_abstain else 0},
    )


def make_unrelated_context_result() -> ContextBuildResult:
    chunk = RerankedResult(
        chunk_id="chunk-remote",
        document_id="doc-remote",
        document_title="Remote Work Handbook",
        department="hr",
        access_level="public",
        section_title="Remote Work Practices",
        text="Remote work uses written updates, asynchronous communication, and clear availability norms.",
        original_score=0.6,
        rerank_score=0.6,
        final_score=0.6,
        retrieval_method="dense_only",
    )
    citation = Citation(
        source_id=1,
        chunk_id=chunk.chunk_id,
        document_id=chunk.document_id,
        document_title=chunk.document_title,
        department=chunk.department,
        section_title=chunk.section_title,
        access_level=chunk.access_level,
        score=chunk.final_score,
    )
    return ContextBuildResult(
        query="What is the company's cafeteria lunch menu?",
        context_text=(
            "[1]\nDocument: Remote Work Handbook\nSection: Remote Work Practices\n"
            "Text:\nRemote work uses written updates and clear availability norms."
        ),
        citations=[citation],
        included_chunks=[chunk],
        safe_abstain=False,
        debug={"context_word_count": 12, "included_chunk_count": 1},
    )


def test_safe_abstain_does_not_call_llm() -> None:
    client = RecordingLLMClient()
    generator = AnswerGenerator(llm_client=client)

    result = generator.generate_from_context("question", make_context_result(safe_abstain=True))

    assert client.calls == 0
    assert result.answer == SAFE_ABSTAIN_MESSAGE
    assert result.debug["llm_called"] is False


def test_authorized_context_calls_llm_and_returns_citations() -> None:
    client = RecordingLLMClient("Use approval details [1]")
    result = AnswerGenerator(llm_client=client).generate_from_context(
        "What is the invoice approval limit?",
        make_context_result(),
    )

    assert client.calls == 1
    assert result.citations
    assert result.debug["llm_called"] is True


def test_missing_citation_marker_is_appended() -> None:
    client = RecordingLLMClient("Use approval details")
    result = AnswerGenerator(llm_client=client).generate_from_context(
        "What is the invoice approval limit?",
        make_context_result(),
    )

    assert result.answer.endswith("[1]")


def test_unsupported_evidence_does_not_call_llm() -> None:
    client = RecordingLLMClient("This should not be used [1]")
    result = AnswerGenerator(llm_client=client).generate_from_context(
        "What is the company's cafeteria lunch menu?",
        make_unrelated_context_result(),
    )

    assert client.calls == 0
    assert result.debug["llm_called"] is False
    assert result.debug["evidence_gate"]["is_supported"] is False


def test_unsupported_evidence_returns_safe_abstention() -> None:
    result = AnswerGenerator().generate_from_context(
        "What is the company's cafeteria lunch menu?",
        make_unrelated_context_result(),
    )

    assert result.safe_abstain is True
    assert result.citations == []
    assert result.answer == SAFE_ABSTAIN_MESSAGE


def test_supported_evidence_still_calls_llm() -> None:
    client = RecordingLLMClient("Use approval details [1]")
    result = AnswerGenerator(llm_client=client).generate_from_context(
        "What is the invoice approval limit?",
        make_context_result(),
    )

    assert client.calls == 1
    assert result.safe_abstain is False
    assert result.debug["evidence_gate"]["is_supported"] is True


def test_end_to_end_finance_user_invoice_query_returns_answer_and_citations(tmp_path) -> None:
    create_sample_docs(tmp_path)
    _, chunks = ingest_directory(tmp_path)

    result = AnswerGenerator().generate(
        "What is the invoice approval limit?",
        "finance_user",
        chunks,
        top_k=5,
    )

    assert result.safe_abstain is False
    assert result.answer
    assert "[1]" in result.answer
    assert result.citations


def test_end_to_end_intern_invoice_query_safe_abstains(tmp_path) -> None:
    create_sample_docs(tmp_path)
    _, chunks = ingest_directory(tmp_path)

    result = AnswerGenerator().generate(
        "What is the invoice approval limit?",
        "intern_user",
        chunks,
        top_k=5,
    )

    assert result.safe_abstain is True
    assert result.citations == []
    assert result.answer == SAFE_ABSTAIN_MESSAGE


def test_end_to_end_engineer_bad_release_query_returns_engineering_answer(tmp_path) -> None:
    create_sample_docs(tmp_path)
    _, chunks = ingest_directory(tmp_path)

    result = AnswerGenerator().generate(
        "How do we restore production after a bad release?",
        "engineer_user",
        chunks,
        top_k=5,
    )

    assert result.safe_abstain is False
    assert result.citations
    assert any(citation.department == "engineering" for citation in result.citations)
    assert "[1]" in result.answer


def test_unauthorized_output_debug_does_not_leak_titles(tmp_path) -> None:
    create_sample_docs(tmp_path)
    _, chunks = ingest_directory(tmp_path)

    invoice_result = AnswerGenerator().generate(
        "What is the invoice approval limit?",
        "intern_user",
        chunks,
        top_k=5,
    )
    rollback_result = AnswerGenerator().generate(
        "How do we restore production after a bad release?",
        "hr_user",
        chunks,
        top_k=5,
    )
    nda_result = AnswerGenerator().generate("NDA policy", "intern_user", chunks, top_k=5)

    combined = f"{invoice_result} {rollback_result} {nda_result}"
    assert "Invoice Approval Policy" not in combined
    assert "Rollback Procedure" not in combined
    assert "NDA Policy" not in combined
