"""Deterministic evaluation metrics for the secure context pipeline."""

from __future__ import annotations

import math
import re

from app.schemas import Citation
from app.security.access_control import SAFE_ABSTAIN_MESSAGE


def normalize_text(text: str) -> str:
    """Lowercase, trim, and collapse whitespace."""
    return " ".join(str(text).lower().strip().split())


def document_hit(retrieved_titles: list[str], expected_titles: list[str]) -> bool:
    """Return true when any expected title is found in retrieved titles."""
    if not retrieved_titles or not expected_titles:
        return False
    return any(
        _title_matches(retrieved_title, expected_title)
        for retrieved_title in retrieved_titles
        for expected_title in expected_titles
    )


def department_hit(retrieved_departments: list[str], expected_departments: list[str]) -> bool:
    """Return true when any retrieved department matches an expected department."""
    retrieved = {normalize_text(department) for department in retrieved_departments}
    expected = {normalize_text(department) for department in expected_departments}
    return bool(retrieved and expected and retrieved.intersection(expected))


def recall_at_k(retrieved_titles: list[str], expected_titles: list[str], k: int) -> float:
    """Compute document-title recall over the top-k retrieved titles."""
    if not expected_titles:
        return 0.0
    top_titles = retrieved_titles[: max(k, 0)]
    expected_unique = _unique_normalized(expected_titles)
    hits = sum(1 for expected_title in expected_unique if document_hit(top_titles, [expected_title]))
    return safe_divide(hits, len(expected_unique))


def mrr(retrieved_titles: list[str], expected_titles: list[str]) -> float:
    """Compute mean reciprocal rank for the first relevant document."""
    if not expected_titles:
        return 0.0
    for index, retrieved_title in enumerate(retrieved_titles, start=1):
        if document_hit([retrieved_title], expected_titles):
            return 1.0 / index
    return 0.0


def ndcg_at_k(retrieved_titles: list[str], expected_titles: list[str], k: int) -> float:
    """Compute binary nDCG@k for document-title relevance."""
    if not expected_titles:
        return 0.0
    top_titles = retrieved_titles[: max(k, 0)]
    gains = [
        1.0 if document_hit([retrieved_title], expected_titles) else 0.0
        for retrieved_title in top_titles
    ]
    dcg = sum(gain / math.log2(rank + 1) for rank, gain in enumerate(gains, start=1))
    ideal_hits = min(len(_unique_normalized(expected_titles)), max(k, 0))
    idcg = sum(1.0 / math.log2(rank + 1) for rank in range(1, ideal_hits + 1))
    return safe_divide(dcg, idcg)


def citation_presence(answer: str, citation_count: int, should_abstain: bool) -> bool:
    """Check citation behavior for answer and abstention cases."""
    if should_abstain:
        return citation_count == 0
    return citation_count > 0 and re.search(r"\[\d+\]", answer) is not None


def abstention_correct(actual_safe_abstain: bool, expected_should_abstain: bool) -> bool:
    """Return whether abstention matched the expected behavior."""
    return actual_safe_abstain is expected_should_abstain


def restricted_leak_detected(output_text: str, forbidden_terms: list[str]) -> bool:
    """Detect forbidden terms by normalized substring matching."""
    normalized_output = normalize_text(output_text)
    return any(
        normalize_text(term) in normalized_output
        for term in forbidden_terms
        if normalize_text(term)
    )


def grounded_answer_heuristic(answer: str, citations: list[Citation], should_abstain: bool) -> bool:
    """Apply a deterministic groundedness proxy for answer output."""
    normalized_answer = normalize_text(answer)
    if should_abstain:
        return (
            SAFE_ABSTAIN_MESSAGE.lower() in normalized_answer
            and len(citations) == 0
        )
    return bool(answer.strip()) and len(citations) > 0


def safe_divide(numerator: float, denominator: float) -> float:
    """Divide without raising when the denominator is zero."""
    if denominator == 0:
        return 0.0
    return numerator / denominator


def _title_matches(retrieved_title: str, expected_title: str) -> bool:
    retrieved = normalize_text(retrieved_title)
    expected = normalize_text(expected_title)
    return bool(retrieved and expected and (retrieved == expected or expected in retrieved or retrieved in expected))


def _unique_normalized(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        normalized = normalize_text(value)
        if normalized and normalized not in seen:
            seen.add(normalized)
            unique.append(value)
    return unique
