from app.context_engine.retrieval_router import RetrievalRouter


def test_metadata_query_routes_to_metadata_lookup() -> None:
    plan = RetrievalRouter().build_plan("Show documents in finance")

    assert plan.retrieval_mode == "metadata_lookup"
    assert plan.candidate_k == 50
    assert plan.top_k == 20


def test_section_query_routes_to_section_lookup() -> None:
    plan = RetrievalRouter().build_plan("What section explains data retention?")

    assert plan.retrieval_mode == "section_lookup"


def test_exact_lookup_routes_with_exact_reason() -> None:
    plan = RetrievalRouter().build_plan("NDA policy")

    assert plan.retrieval_mode in {"bm25_only", "hybrid"}
    assert "exact" in plan.reason.lower()


def test_paraphrased_vague_query_routes_to_dense_or_hybrid() -> None:
    plan = RetrievalRouter().build_plan("How should we handle confusing internal guidance?")

    assert plan.retrieval_mode in {"dense_only", "hybrid"}


def test_normal_department_query_routes_to_hybrid() -> None:
    plan = RetrievalRouter().build_plan("What is the invoice approval limit?")

    assert plan.retrieval_mode == "hybrid"


def test_comparison_query_uses_larger_limits() -> None:
    plan = RetrievalRouter().build_plan("Compare remote work policy and contractor policy")

    assert plan.retrieval_mode == "hybrid"
    assert plan.candidate_k == 30
    assert plan.top_k == 8


def test_filters_include_department_hint() -> None:
    plan = RetrievalRouter().build_plan("database backup schedule")

    assert plan.filters["department"] == "engineering"
    assert plan.filters["intent"] == plan.analysis.intent
    assert "database backup" in plan.filters["detected_terms"]


def test_plan_is_deterministic() -> None:
    router = RetrievalRouter()

    first = router.build_plan("How do I get paid back for travel costs?")
    second = router.build_plan("How do I get paid back for travel costs?")

    assert first == second
