from app.context_engine.query_analyzer import QueryAnalyzer


def test_procedure_detection_for_bad_release() -> None:
    analysis = QueryAnalyzer().analyze("How do we restore production after a bad release?")

    assert analysis.intent in {"procedure", "troubleshooting"}
    assert analysis.department_hint == "engineering"
    assert analysis.needs_step_by_step_answer is True
    assert analysis.needs_semantic_search is True


def test_finance_policy_exact_signals() -> None:
    analysis = QueryAnalyzer().analyze("What is the invoice approval limit?")

    assert analysis.intent in {"policy_question", "exact_lookup"}
    assert analysis.department_hint == "finance"
    assert analysis.needs_exact_terms is True
    assert "invoice approval" in analysis.detected_terms


def test_legal_exact_lookup() -> None:
    analysis = QueryAnalyzer().analyze("NDA policy")

    assert analysis.department_hint == "legal"
    assert analysis.needs_exact_terms is True
    assert "NDA" in analysis.detected_terms


def test_hr_paraphrase() -> None:
    analysis = QueryAnalyzer().analyze("How do I get paid back for travel costs?")

    assert analysis.department_hint == "hr"
    assert analysis.needs_semantic_search is True


def test_metadata_request() -> None:
    analysis = QueryAnalyzer().analyze("Show documents in finance")

    assert analysis.intent == "metadata_request"
    assert analysis.department_hint == "finance"
    assert analysis.needs_metadata_filter is True


def test_section_request() -> None:
    analysis = QueryAnalyzer().analyze("What section explains data retention?")

    assert analysis.intent == "section_request"
    assert analysis.needs_section_lookup is True
    assert analysis.department_hint == "legal"


def test_comparison_request() -> None:
    analysis = QueryAnalyzer().analyze("Compare remote work policy and contractor policy")

    assert analysis.intent == "comparison"
    assert analysis.needs_comparison is True


def test_ambiguous_query() -> None:
    analysis = QueryAnalyzer().analyze("help")

    assert analysis.intent == "ambiguous"
    assert analysis.confidence <= 0.6
