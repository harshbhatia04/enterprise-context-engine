import pytest
from fastapi import HTTPException

from app.security.auth import (
    AUTH_API_KEY,
    AUTH_OFF,
    AuthContext,
    get_auth_context,
    get_auth_mode,
    parse_demo_api_keys,
    resolve_request_user,
)


def test_default_auth_mode_is_off(monkeypatch) -> None:
    monkeypatch.delenv("ECE_AUTH_MODE", raising=False)

    assert get_auth_mode() == AUTH_OFF


def test_parse_demo_api_keys_parses_env_string() -> None:
    mapping = parse_demo_api_keys("finance_user:finance-token, intern_user: intern-token")

    assert mapping == {
        "finance-token": "finance_user",
        "intern-token": "intern_user",
    }


def test_api_key_mode_accepts_bearer_token(monkeypatch) -> None:
    monkeypatch.setenv("ECE_AUTH_MODE", AUTH_API_KEY)
    monkeypatch.setenv("ECE_DEMO_API_KEYS", "finance_user:finance-token")

    context = get_auth_context(authorization="Bearer finance-token", x_api_key=None)

    assert context.authenticated is True
    assert context.user_id == "finance_user"


def test_api_key_mode_accepts_x_api_key(monkeypatch) -> None:
    monkeypatch.setenv("ECE_AUTH_MODE", AUTH_API_KEY)
    monkeypatch.setenv("ECE_DEMO_API_KEYS", "hr_user:hr-token")

    context = get_auth_context(authorization=None, x_api_key="hr-token")

    assert context.authenticated is True
    assert context.user_id == "hr_user"


def test_missing_token_raises_401(monkeypatch) -> None:
    monkeypatch.setenv("ECE_AUTH_MODE", AUTH_API_KEY)

    with pytest.raises(HTTPException) as exc:
        get_auth_context(authorization=None, x_api_key=None)

    assert exc.value.status_code == 401


def test_invalid_token_raises_401(monkeypatch) -> None:
    monkeypatch.setenv("ECE_AUTH_MODE", AUTH_API_KEY)
    monkeypatch.setenv("ECE_DEMO_API_KEYS", "hr_user:hr-token")

    with pytest.raises(HTTPException) as exc:
        get_auth_context(authorization="Bearer wrong-token", x_api_key=None)

    assert exc.value.status_code == 401


def test_resolve_request_user_returns_request_user_in_off_mode() -> None:
    context = AuthContext(auth_mode=AUTH_OFF, authenticated=False)

    assert resolve_request_user("finance_user", context) == "finance_user"


def test_resolve_request_user_rejects_spoofing_in_api_key_mode() -> None:
    context = AuthContext(auth_mode=AUTH_API_KEY, authenticated=True, user_id="finance_user")

    with pytest.raises(HTTPException) as exc:
        resolve_request_user("intern_user", context)

    assert exc.value.status_code == 403


def test_resolve_request_user_accepts_matching_authenticated_user() -> None:
    context = AuthContext(auth_mode=AUTH_API_KEY, authenticated=True, user_id="finance_user")

    assert resolve_request_user("finance_user", context) == "finance_user"
