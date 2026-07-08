import pytest
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock

from backend.core.security.middlewares import ZeroTrustMiddleware

# Build a mock FastAPI app for middleware testing
app = FastAPI()
app.add_middleware(ZeroTrustMiddleware)

@app.get("/api/v1/auth/verify-email")
def mock_verify_email():
    return {"message": "reached_verify_email"}

@app.post("/api/v1/auth/resend-verification")
def mock_resend_verification():
    return {"message": "reached_resend_verification"}

@app.get("/api/v1/demo/pipeline/health")
def mock_demo_pipeline_health():
    return {"llm_ok": True, "groq_fallback_enabled": True}

@app.get("/api/v1/demo/pipeline/health-sensitive")
def mock_demo_pipeline_health_sensitive():
    return {"message": "should_not_be_public"}

@app.get("/api/v1/secure-endpoint")
def mock_secure():
    return {"message": "reached_secure"}

def test_zerotrust_middleware_bypasses_verify_email():
    client = TestClient(app)
    
    # 1. verify-email should bypass middleware (returns 200 instead of 401)
    response = client.get("/api/v1/auth/verify-email")
    assert response.status_code == 200
    assert response.json() == {"message": "reached_verify_email"}

    # 2. resend-verification should bypass middleware (returns 200 instead of 401)
    response = client.post("/api/v1/auth/resend-verification")
    assert response.status_code == 200
    assert response.json() == {"message": "reached_resend_verification"}

    # 3. secure endpoint should be blocked (returns 401)
    response = client.get("/api/v1/secure-endpoint")
    assert response.status_code == 401
    assert response.json() == {"detail": "Missing authentication credentials"}


def test_zerotrust_middleware_bypasses_only_demo_pipeline_health():
    client = TestClient(app)

    response = client.get("/api/v1/demo/pipeline/health")
    assert response.status_code == 200
    assert response.json() == {"llm_ok": True, "groq_fallback_enabled": True}

    response = client.get("/api/v1/demo/pipeline/health-sensitive")
    assert response.status_code == 401
    assert response.json() == {"detail": "Missing authentication credentials"}
