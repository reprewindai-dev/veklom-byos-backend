"""Tests for the authenticated CAPPO workspace assertion exchange."""

from types import SimpleNamespace

import jwt
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from backend.apps.api.routers import auth


def _app(user=None):
    app = FastAPI()
    app.include_router(auth.router, prefix="/api/v1")

    async def override_user():
        if user is None:
            raise HTTPException(status_code=401, detail="Missing authentication credentials")
        return user

    app.dependency_overrides[auth.get_current_user] = override_user
    return app


def _user(workspace_id="workspace-1"):
    return SimpleNamespace(
        id="user-1",
        workspace_id=workspace_id,
        role="OWNER",
    )


def test_cappo_token_requires_authentication():
    response = TestClient(_app()).post("/api/v1/auth/cappo-token")

    assert response.status_code == 401
    assert response.json() == {"detail": "Missing authentication credentials"}


def test_cappo_token_rejects_user_without_workspace():
    response = TestClient(_app(_user(None))).post("/api/v1/auth/cappo-token")

    assert response.status_code == 403
    assert response.json() == {"detail": {"error": "WORKSPACE_CONTEXT_MISSING"}}


def test_cappo_token_fails_closed_when_signing_key_is_unconfigured(monkeypatch):
    monkeypatch.delenv("CAPPO_ASSERTION_SIGNING_KEY", raising=False)

    response = TestClient(_app(_user())).post("/api/v1/auth/cappo-token")

    assert response.status_code == 503
    assert response.json() == {"detail": {"error": "CAPPO_ASSERTION_UNCONFIGURED"}}


def test_cappo_token_is_an_ed25519_workspace_assertion(monkeypatch):
    private_key = Ed25519PrivateKey.generate()
    seed = private_key.private_bytes_raw()
    monkeypatch.setenv("CAPPO_ASSERTION_SIGNING_KEY", seed.hex())
    monkeypatch.setenv("CAPPO_ASSERTION_ISSUER", "https://issuer.test")
    monkeypatch.setenv("CAPPO_ASSERTION_AUDIENCE", "https://cappo.test")

    response = TestClient(_app(_user("workspace-7"))).post("/api/v1/auth/cappo-token")

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 120

    public_key = private_key.public_key()
    claims = jwt.decode(
        body["access_token"],
        public_key,
        algorithms=["EdDSA"],
        issuer="https://issuer.test",
        audience="https://cappo.test",
    )
    assert claims["sub"] == "user-1"
    assert claims["workspace_id"] == "workspace-7"
    assert claims["role"] == "OWNER"
    assert claims["iss"] == "https://issuer.test"
    assert claims["aud"] == "https://cappo.test"
    assert claims["exp"] - claims["iat"] <= 120
    assert claims["exp"] > claims["iat"]
    assert claims["jti"]
