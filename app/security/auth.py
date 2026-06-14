"""Optional API-key authentication simulation for local enterprise demos."""

from __future__ import annotations

import os

from fastapi import Header, HTTPException
from pydantic import BaseModel

AUTH_OFF = "off"
AUTH_API_KEY = "api_key"
DEFAULT_DEMO_API_KEYS = (
    "admin_user:dev-admin-key,"
    "finance_user:dev-finance-key,"
    "hr_user:dev-hr-key,"
    "engineer_user:dev-engineer-key,"
    "legal_user:dev-legal-key,"
    "intern_user:dev-intern-key"
)


class AuthContext(BaseModel):
    auth_mode: str
    authenticated: bool
    user_id: str | None = None
    reason: str | None = None


def get_auth_mode() -> str:
    """Return configured auth mode, defaulting safely to off."""
    mode = os.getenv("ECE_AUTH_MODE", AUTH_OFF).strip().lower()
    if mode not in {AUTH_OFF, AUTH_API_KEY}:
        return AUTH_OFF
    return mode


def parse_demo_api_keys(raw: str | None = None) -> dict[str, str]:
    """Parse demo API keys from user_id:token pairs into token -> user_id."""
    source = DEFAULT_DEMO_API_KEYS if raw is None else raw
    mapping: dict[str, str] = {}
    for item in source.split(","):
        if not item.strip() or ":" not in item:
            continue
        user_id, token = [part.strip() for part in item.split(":", 1)]
        if user_id and token:
            mapping[token] = user_id
    return mapping


def get_auth_context(
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None),
) -> AuthContext:
    """Resolve request auth from Authorization bearer or X-API-Key headers."""
    auth_mode = get_auth_mode()
    if auth_mode == AUTH_OFF:
        return AuthContext(auth_mode=AUTH_OFF, authenticated=False)

    token = _extract_token(authorization, x_api_key)
    if not token:
        raise HTTPException(status_code=401, detail="Missing API key or bearer token")

    user_id = parse_demo_api_keys(os.getenv("ECE_DEMO_API_KEYS")).get(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid API key or bearer token")

    return AuthContext(auth_mode=AUTH_API_KEY, authenticated=True, user_id=user_id)


def resolve_request_user(request_user_id: str, auth_context: AuthContext) -> str:
    """Resolve effective user identity and reject spoofing when auth is enabled."""
    if auth_context.auth_mode == AUTH_OFF:
        return request_user_id

    if not auth_context.authenticated or not auth_context.user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    if request_user_id != auth_context.user_id:
        raise HTTPException(status_code=403, detail="Authenticated user does not match request user_id")

    return auth_context.user_id


def _extract_token(authorization: str | None, x_api_key: str | None) -> str | None:
    if authorization:
        scheme, _, token = authorization.strip().partition(" ")
        if scheme.lower() == "bearer" and token.strip():
            return token.strip()
    if x_api_key and x_api_key.strip():
        return x_api_key.strip()
    return None
