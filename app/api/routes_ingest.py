"""Ingestion routes for sample enterprise documents."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas import DataSourceRequest, DataSourceResponse, IngestResponse
from app.storage.app_state import (
    SAMPLE_DOCS,
    get_available_data_sources,
    load_data_source,
)

router = APIRouter(tags=["ingest"])


@router.post("/ingest/sample", response_model=IngestResponse)
def ingest_sample_docs() -> IngestResponse:
    """Load bundled sample docs into process memory once."""
    state = load_data_source(SAMPLE_DOCS)
    return IngestResponse(
        status="ok",
        documents_ingested=len(state.documents),
        chunks_created=len(state.chunks),
        active_data_source=state.active_data_source,
    )


@router.get("/data-sources")
def data_sources() -> list[dict]:
    """Return available selectable data sources."""
    return get_available_data_sources()


@router.post("/ingest/data-source", response_model=DataSourceResponse)
def ingest_data_source(request: DataSourceRequest) -> DataSourceResponse:
    """Load a supported data source mode into process memory."""
    try:
        state = load_data_source(request.mode)
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return DataSourceResponse(
        status="success",
        active_data_source=state.active_data_source,
        documents_ingested=len(state.documents),
        chunks_created=len(state.chunks),
    )
