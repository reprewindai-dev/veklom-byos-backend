import asyncio
import base64
import hashlib
import hmac
import time
from datetime import datetime, timedelta, timezone

import pyotp
import pytest
from fastapi import HTTPException, Request
from jose import jwt

from backend.apps.api.routers import auth  # billing router removed; import pruned
from backend.core.config.settings import settings
from backend.core.security.auth import verify_token
from backend.core.security.payment_proof import require_payment_proof
from backend.core.security.webhook_signatures import (
    verify_github_signature,
    verify_resend_signature,
)


def make_request(headers=None):
    return Request({
        "type": "http",
        "method": "POST",
        "path": "/api/v1/governed/execute",
        "headers": [(key.lower().encode(), value.encode()) for key, value in (headers or {}).items()],
        "query_string": b"",
        "client": ("127.0.0.1", 1234),
        "server": ("testserver", 80),
        "scheme": "http",
    })


def test_static_auth_bypass_tokens_are_rejected():
    for token in ("{VEKLOM_API_TOKEN}", "VEKLOM_API_TOKEN", "VEKLOM_LOOMAL_SOT_TOKEN"):
        with pytest.raises(HTTPException) as exc:
            verify_token(token)
        assert exc.value.status_code == 401


def test_development_jwt_secret_is_not_accepted(monkeypatch):
    token = jwt.encode(
        {"sub": "user-1", "aud": settings.JWT_EXPECTED_AUDIENCE, "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
        "test_secret_key_for_development_only",
        algorithm=settings.JWT_ALGORITHM,
    )
    with pytest.raises(HTTPException):
        verify_token(token)


def test_wrong_jwt_audience_is_always_rejected(monkeypatch):
    monkeypatch.setattr(settings, "JWT_AUD_ENFORCEMENT", "warn")
    token = jwt.encode(
        {"sub": "user-1", "aud": "wrong-audience", "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )
    with pytest.raises(HTTPException):
        verify_token(token)


def test_payment_proof_requires_middleware_verification():
    request = make_request({"X-Payment": "0x" + "1" * 64})
    with pytest.raises(HTTPException) as exc:
        asyncio.run(require_payment_proof(request))
    assert exc.value.status_code == 402


def test_server_owned_plan_amount_ignores_client_pricing():
    assert billing._plan_amount_cents("starter") == 250000


def test_unknown_plan_has_no_fallback_price():
    with pytest.raises(HTTPException) as exc:
        billing._plan_amount_cents("not-a-real-plan")
    assert exc.value.status_code == 400


def test_resend_signature_accepts_valid_current_delivery():
    secret = "whsec_" + base64.b64encode(b"resend-secret").decode()
    delivery_id = "evt_123"
    timestamp = str(int(time.time()))
    body = b'{"type":"email.delivered"}'
    signed = f"{delivery_id}.{timestamp}.".encode() + body
    digest = base64.b64encode(hmac.new(b"resend-secret", signed, hashlib.sha256).digest()).decode()
    assert verify_resend_signature(body, secret, delivery_id, timestamp, f"v1,{digest}")


def test_resend_signature_rejects_stale_delivery():
    secret = "whsec_" + base64.b64encode(b"resend-secret").decode()
    body = b"{}"
    assert not verify_resend_signature(body, secret, "evt_123", str(int(time.time()) - 601), "v1,invalid")


def test_github_signature_requires_exact_body():
    secret = "github-secret"
    body = b'{"ref":"refs/heads/main"}'
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    assert verify_github_signature(body, secret, f"sha256={digest}")
    assert not verify_github_signature(body + b" ", secret, f"sha256={digest}")


def test_github_redirect_rejects_external_origin():
    assert auth._safe_github_redirect("https://attacker.example/steal") == f"{auth.CONTROL_PLANE_URL}/dashboard/"


def test_github_redirect_allows_only_control_plane_paths():
    result = auth._safe_github_redirect("/dashboard/settings")
    assert result == f"{auth.CONTROL_PLANE_URL}/dashboard/settings"

def test_mfa_helper_uses_secret_and_rejects_wrong_code():
    secret = pyotp.random_base32()
    assert auth._verify_mfa_code(secret, pyotp.TOTP(secret).now())
    assert not auth._verify_mfa_code(secret, "000000")
