"""Evaluation runner for the full secure answer-generation pipeline."""

from __future__ import annotations

from time import perf_counter

from app.evaluation.metrics import (
    abstention_correct,
    citation_presence,
    department_hit,
    document_hit,
    grounded_answer_heuristic,
    mrr,
    ndcg_at_k,
    recall_at_k,
    restricted_leak_detected,
    safe_divide,
)
from app.generation.answer_generator import AnswerGenerator
from app.schemas import Chunk, EvalExample, EvalExampleResult, EvalSummary


class EvalRunner:
    """Run deterministic evaluations against the secure answer pipeline."""

    def __init__(self, chunks: list[Chunk], answer_generator: AnswerGenerator | None = None) -> None:
        self.chunks = list(chunks)
        self.answer_generator = answer_generator or AnswerGenerator()

    def run_example(self, example: EvalExample) -> EvalExampleResult:
        """Run one eval example and return detailed deterministic metrics."""
        started = perf_counter()
        generated = self.answer_generator.generate(
            query=example.question,
            user_id=example.user_id,
            chunks=self.chunks,
            top_k=5,
        )
        latency_ms = (perf_counter() - started) * 1000

        citation_titles = _unique([citation.document_title for citation in generated.citations])
        citation_departments = _unique([citation.department for citation in generated.citations])
        retrieval_mode = generated.debug.get("retrieval_mode")
        forbidden_terms = (
            example.expected_document_titles + example.expected_terms
            if not example.expected_access_allowed
            else []
        )
        leak_output = f"{generated.answer} {generated.debug}"

        metric_values = {
            "document_hit": document_hit(citation_titles, example.expected_document_titles),
            "department_hit": department_hit(citation_departments, example.expected_departments),
            "recall_at_5": recall_at_k(citation_titles, example.expected_document_titles, 5),
            "mrr": mrr(citation_titles, example.expected_document_titles),
            "ndcg_at_5": ndcg_at_k(citation_titles, example.expected_document_titles, 5),
            "citation_presence": citation_presence(
                generated.answer,
                len(generated.citations),
                example.answer_should_abstain,
            ),
            "abstention_correct": abstention_correct(
                generated.safe_abstain,
                example.answer_should_abstain,
            ),
            "grounded_answer_heuristic": grounded_answer_heuristic(
                generated.answer,
                generated.citations,
                example.answer_should_abstain,
            ),
            "retrieval_mode_match": _retrieval_mode_acceptable(
                retrieval_mode,
                example.expected_retrieval_mode,
            ),
            "restricted_leak_detected": restricted_leak_detected(leak_output, forbidden_terms),
        }

        failure_reasons = self._failure_reasons(example, metric_values, generated.safe_abstain, len(generated.citations))

        return EvalExampleResult(
            example_id=example.example_id,
            question=example.question,
            user_id=example.user_id,
            answer=generated.answer,
            safe_abstain=generated.safe_abstain,
            citations=generated.citations,
            retrieved_document_titles=citation_titles,
            retrieved_departments=citation_departments,
            retrieval_mode=retrieval_mode,
            latency_ms=latency_ms,
            metrics=metric_values,
            passed=not failure_reasons,
            failure_reasons=failure_reasons,
            debug={
                "expected_access_allowed": example.expected_access_allowed,
                "answer_should_abstain": example.answer_should_abstain,
                "expected_retrieval_mode": example.expected_retrieval_mode,
                "answer_debug": generated.debug,
            },
        )

    def run(self, examples: list[EvalExample]) -> EvalSummary:
        """Run all examples and aggregate summary metrics."""
        results = [self.run_example(example) for example in examples]
        total = len(results)
        passed = sum(1 for result in results if result.passed)
        authorized = [
            result
            for result in results
            if result.debug.get("expected_access_allowed") is True
            and result.debug.get("answer_should_abstain") is False
        ]
        unauthorized = [
            result for result in results if result.debug.get("expected_access_allowed") is False
        ]
        mode_expected = [
            result
            for result in results
            if result.debug.get("expected_retrieval_mode") is not None
            and result.debug.get("answer_should_abstain") is False
        ]

        metrics = {
            "pass_rate": safe_divide(passed, total),
            "retrieval_document_hit_rate": _mean_metric(authorized, "document_hit"),
            "retrieval_department_hit_rate": _mean_metric(authorized, "department_hit"),
            "mean_recall_at_5": _mean_metric(authorized, "recall_at_5"),
            "mean_mrr": _mean_metric(authorized, "mrr"),
            "mean_ndcg_at_5": _mean_metric(authorized, "ndcg_at_5"),
            "citation_presence_rate": _mean_metric(results, "citation_presence"),
            "abstention_accuracy": _mean_metric(results, "abstention_correct"),
            "grounded_answer_rate": _mean_metric(results, "grounded_answer_heuristic"),
            "restricted_leak_rate": _mean_metric(unauthorized, "restricted_leak_detected"),
            "retrieval_mode_accuracy": _mean_metric(mode_expected, "retrieval_mode_match"),
            "average_latency_ms": safe_divide(
                sum(result.latency_ms for result in results),
                total,
            ),
            "authorized_count": len(authorized),
            "unauthorized_count": len(unauthorized),
        }

        return EvalSummary(
            total_examples=total,
            passed_examples=passed,
            failed_examples=total - passed,
            metrics=metrics,
            results=results,
        )

    @staticmethod
    def _failure_reasons(
        example: EvalExample,
        metrics: dict,
        actual_safe_abstain: bool,
        citation_count: int,
    ) -> list[str]:
        reasons: list[str] = []
        if example.answer_should_abstain:
            if not actual_safe_abstain:
                reasons.append("expected safe abstention but got an answer")
            if citation_count:
                reasons.append("expected no citations for abstention query")
            if not metrics["abstention_correct"]:
                reasons.append("abstention behavior did not match expectation")
            if metrics["restricted_leak_detected"]:
                reasons.append("restricted title or term appeared in output/debug")
            return reasons

        if example.expected_access_allowed:
            if actual_safe_abstain:
                reasons.append("expected accessible answer but got safe abstention")
            if not (metrics["document_hit"] or metrics["department_hit"]):
                reasons.append("expected document or department was not surfaced")
            if not metrics["citation_presence"]:
                reasons.append("expected answer citation marker and citation metadata")
            if not metrics["grounded_answer_heuristic"]:
                reasons.append("grounded answer heuristic failed")
            if example.expected_retrieval_mode and not metrics["retrieval_mode_match"]:
                reasons.append("retrieval mode did not match expected mode")
        else:
            if not actual_safe_abstain:
                reasons.append("expected safe abstention but got an answer")
            if citation_count:
                reasons.append("expected no citations for unauthorized query")
            if not metrics["abstention_correct"]:
                reasons.append("abstention behavior did not match expectation")
            if metrics["restricted_leak_detected"]:
                reasons.append("restricted title or term appeared in output/debug")
        return reasons


def _retrieval_mode_acceptable(actual_mode: str | None, expected_mode: str | None) -> bool:
    if expected_mode is None:
        return True
    if actual_mode == expected_mode:
        return True
    return actual_mode == "hybrid" and expected_mode in {"bm25_only", "dense_only"}


def _mean_metric(results: list[EvalExampleResult], metric_name: str) -> float:
    if not results:
        return 0.0
    return safe_divide(
        sum(1.0 if result.metrics.get(metric_name) is True else float(result.metrics.get(metric_name, 0.0)) for result in results),
        len(results),
    )


def _unique(values: list[str]) -> list[str]:
    unique: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value not in seen:
            seen.add(value)
            unique.append(value)
    return unique
