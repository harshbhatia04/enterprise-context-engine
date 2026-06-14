def test_key_imports() -> None:
    import app.main  # noqa: F401
    from app.evaluation.eval_runner import EvalRunner
    from app.generation.answer_generator import AnswerGenerator
    from app.storage.app_state import get_app_state

    assert AnswerGenerator
    assert EvalRunner
    assert get_app_state


def test_optional_qdrant_import_guard() -> None:
    import app.retrieval.qdrant_retriever  # noqa: F401
