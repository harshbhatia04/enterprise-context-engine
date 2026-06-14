"""Query routes for the secure answer-generation pipeline."""

from __future__ import annotations

from dataclasses import asdict
from time import perf_counter

from fastapi import APIRouter, Depends, HTTPException, Query

from app.generation.answer_generator import AnswerGenerator
from app.schemas import QueryRequest, QueryResponse
from app.security.auth import AuthContext, get_auth_context, resolve_request_user
from app.storage.app_state import create_query_log, ensure_active_data_source_loaded, list_query_logs

router = APIRouter(tags=["query"])


@router.post("/query", response_model=QueryResponse)
def query(
    request: QueryRequest,
    auth_context: AuthContext = Depends(get_auth_context),
) -> QueryResponse:
    """Answer a user query using the existing secure pipeline."""
    state = ensure_active_data_source_loaded()
    resolved_user_id = resolve_request_user(request.user_id, auth_context)
    started = perf_counter()
    try:
        result = AnswerGenerator().generate(
            query=request.query,
            user_id=resolved_user_id,
            chunks=state.chunks,
            top_k=request.top_k,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    latency_ms = (perf_counter() - started) * 1000
    response_debug = {
        **result.debug,
        "active_data_source": state.active_data_source,
        "auth_mode": auth_context.auth_mode,
        "authenticated_user_id": auth_context.user_id if auth_context.authenticated else None,
    }

    create_query_log(
        user_id=resolved_user_id,
        query=request.query,
        answer=result.answer,
        safe_abstain=result.safe_abstain,
        citation_count=len(result.citations),
        retrieval_mode=result.debug.get("retrieval_mode"),
        intent=result.debug.get("intent"),
        latency_ms=latency_ms,
        debug=response_debug,
    )

    return QueryResponse(
        query=result.query,
        user_id=resolved_user_id,
        answer=result.answer,
        safe_abstain=result.safe_abstain,
        citations=[asdict(citation) for citation in result.citations],
        debug=response_debug,
    )


@router.get("/logs")
def list_logs(limit: int = Query(default=50, ge=1, le=500)) -> list[dict]:
    """Return recent sanitized query logs."""
    ensure_active_data_source_loaded()
    return [asdict(entry) for entry in list_query_logs(limit=limit)]
