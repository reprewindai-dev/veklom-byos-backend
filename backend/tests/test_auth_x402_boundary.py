"""Regression tests for the canonical x402/authentication boundary."""

import asyncio
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from starlette.requests import Request

from backend.core.security.auth import get_current_user, get_current_user_optional


def _request() -> Request:
    return Request({"type": "http", "method": "GET", "path": "/api/v1/protected", "headers": []})


def test_forged_x402_paid_flag_cannot_authenticate_without_credentials():
    request = _request()
    request.state.x402_paid = True

    with pytest.raises(HTTPException) as exc:
        asyncio.run(get_current_user(request, credentials=None, db=None))

    assert exc.value.status_code == 401
    assert exc.value.detail == "Missing authentication credentials"


def test_forged_x402_paid_flag_does_not_create_optional_agent_identity():
    request = _request()
    request.state.x402_paid = True

    user = asyncio.run(get_current_user_optional(request, credentials=None, db=None))

    assert user.id == "guest"
    assert user.workspace_id == "guest"
    assert user.role == "user"


def test_forged_x402_paid_flag_cannot_bypass_invalid_bearer_token():
    request = _request()
    request.state.x402_paid = True
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="not-a-valid-jwt")

    with pytest.raises(HTTPException) as exc:
        asyncio.run(get_current_user(request, credentials=credentials, db=None))

    assert exc.value.status_code == 401


def test_canonical_auth_contains_no_synthetic_x402_user_shortcut():
    source = Path("backend/core/security/auth.py").read_text(encoding="utf-8")

    assert "MockAgentUser" not in source
    assert "getattr(request.state, \"x402_paid\"" not in source
