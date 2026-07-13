import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from backend.core.cappo.middleware import CappoPolicyMiddleware

app = FastAPI()
app.add_middleware(CappoPolicyMiddleware)

@app.get("/api/v1/cappo/test")
async def test_cappo_route():
    return {"message": "success"}

@app.get("/api/v1/other")
async def test_other_route():
    return {"message": "success"}


class MockTransportContext:
    def __init__(self, verified: bool):
        self.spiffe_verified = verified

class MockTraceContext:
    def __init__(self, status: str):
        self.repo_gate_status = status


@app.middleware("http")
async def mock_amphoteric_middleware(request: Request, call_next):
    # Inject mock contexts for testing based on headers
    if request.headers.get("X-Mock-Missing-Context") == "true":
        pass
    else:
        verified = request.headers.get("X-Mock-Spiffe-Verified", "true").lower() == "true"
        status = request.headers.get("X-Mock-RepoGate-Status", "verified")
        request.state.transport = MockTransportContext(verified)
        request.state.trace = MockTraceContext(status)
    return await call_next(request)


client = TestClient(app)

def test_cappo_middleware_ignores_ungoverned_routes():
    # /api/v1/other should bypass CAPPO middleware
    response = client.get("/api/v1/other", headers={"X-Mock-Missing-Context": "true"})
    assert response.status_code == 200
    assert response.json()["message"] == "success"

def test_cappo_middleware_blocks_missing_context():
    # Missing Amphoteric context entirely
    response = client.get("/api/v1/cappo/test", headers={"X-Mock-Missing-Context": "true"})
    assert response.status_code == 403
    data = response.json()
    assert data["status"] == "security_blocked"
    assert data["error_code"] == "MISSING_AMPHOTERIC_CONTEXT"

def test_cappo_middleware_blocks_unverified_spiffe(monkeypatch):
    import backend.core.cappo.middleware
    original_getattr = getattr
    def mock_getattr(obj, name, default=None):
        if name == "DEBUG_MOCK_SPIFFE": return False
        return original_getattr(obj, name, default)
    monkeypatch.setattr(backend.core.cappo.middleware, "getattr", mock_getattr)
    
    response = client.get("/api/v1/cappo/test", headers={"X-Mock-Spiffe-Verified": "false"})
    assert response.status_code == 403
    data = response.json()
    assert data["error_code"] == "MISSING_SPIFFE_IDENTITY"

def test_cappo_middleware_blocks_unverified_repogate(monkeypatch):
    import backend.core.cappo.middleware
    original_getattr = getattr
    def mock_getattr(obj, name, default=None):
        if name == "DEBUG_MOCK_REPOGATE": return False
        return original_getattr(obj, name, default)
    monkeypatch.setattr(backend.core.cappo.middleware, "getattr", mock_getattr)
    
    response = client.get("/api/v1/cappo/test", headers={"X-Mock-RepoGate-Status": "failed"})
    assert response.status_code == 403
    data = response.json()
    assert data["error_code"] == "MISSING_REPOGATE_ATTESTATION"

def test_cappo_middleware_allows_verified_request():
    response = client.get("/api/v1/cappo/test", headers={
        "X-Mock-Spiffe-Verified": "true",
        "X-Mock-RepoGate-Status": "verified"
    })
    assert response.status_code == 200
    assert response.json()["message"] == "success"
