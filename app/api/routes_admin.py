"""Admin and inspection routes for the API MVP."""

from __future__ import annotations

from fastapi import APIRouter

from app.security.auth import AUTH_API_KEY, get_auth_mode
from app.security.users import list_users
from app.storage.app_state import (
    ensure_active_data_source_loaded,
    get_app_state,
    get_sqlite_path,
    get_storage_backend,
    is_sqlite_enabled,
)

router = APIRouter(tags=["admin"])


@router.get("/users")
def users() -> list[dict]:
    """Return configured demo users."""
    return list_users()


@router.get("/auth/status")
def auth_status() -> dict:
    """Return safe auth-mode metadata without exposing tokens."""
    auth_mode = get_auth_mode()
    return {
        "auth_mode": auth_mode,
        "enabled": auth_mode == AUTH_API_KEY,
    }


@router.get("/documents")
def documents() -> list[dict]:
    """Return document metadata only, never body text."""
    state = ensure_active_data_source_loaded()
    return [
        {
            "document_id": document.document_id,
            "title": document.title,
            "department": document.department,
            "access_level": document.access_level,
            "version": document.version,
            "effective_date": document.effective_date,
            "document_type": document.document_type,
            "source_path": document.source_path,
            "source_name": document.metadata.get("source_name"),
            "source_url": document.metadata.get("source_url"),
        }
        for document in state.documents
    ]


@router.get("/health")
def health() -> dict:
    """Return process-local API health and ingestion counts."""
    state = get_app_state()
    return {
        "status": "ok",
        "is_ingested": state.is_ingested,
        "active_data_source": state.active_data_source,
        "document_count": len(state.documents),
        "chunk_count": len(state.chunks),
        "storage_backend": get_storage_backend(),
        "sqlite_path": get_sqlite_path() if is_sqlite_enabled() else None,
    }
