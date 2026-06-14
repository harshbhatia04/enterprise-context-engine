"""FastAPI entrypoint for the Enterprise Context Engine."""

from __future__ import annotations

from fastapi import FastAPI

from app.api.routes_admin import router as admin_router
from app.api.routes_eval import router as eval_router
from app.api.routes_ingest import router as ingest_router
from app.api.routes_query import router as query_router

APP_TITLE = "Enterprise Context Engine"

app = FastAPI(title=APP_TITLE)
app.include_router(ingest_router)
app.include_router(query_router)
app.include_router(eval_router)
app.include_router(admin_router)


@app.get("/")
def root() -> dict[str, str]:
    """Return a small health payload for humans and tests."""
    return {"name": APP_TITLE, "status": "ok"}
