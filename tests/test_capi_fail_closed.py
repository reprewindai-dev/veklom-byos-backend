import pytest
import json
from fastapi.testclient import TestClient
from backend.apps.api.main import app
from backend.db.models.agent import AgentIdentity
from backend.db.models.authority import AuthorityBundle
from backend.core.database.database import get_db

client = TestClient(app)

@pytest.mark.asyncio
async def test_phase_1_signature_failure():
    """Test 1: Tampered Payload Signature Rejection (Phase 1)"""
    payload = {
        "agent_id": "agent-core-01",
        "pgl_id": "badsig", # Explicitly trigger failure
        "target_protocol": "syscall_execute",
        "action": "fs.write",
        "payload": {
            "path": "/etc/hosts",
            "content": "127.0.0.1 illegal-routing.net"
        }
    }
    response = client.post("/api/v1/capi/execute", json=payload)
    assert response.status_code == 403
    data = response.json()
    assert data["detail"]["error"] == "cAPI_VETO_ENGAGED"
    assert data["detail"]["phase"] == 1
    assert data["detail"]["reason"] == "CRYPTOGRAPHIC_SIGNATURE_INVALID"

@pytest.mark.asyncio
async def test_phase_2_implicit_deny():
    """Test 2: Implicit Deny Enforcement (Phase 2)"""
    # We use a valid-looking pgl_id but an action that won't have an ALLOW rule
    payload = {
        "agent_id": "agent-core-01",
        "pgl_id": "valid_mock_sig",
        "target_protocol": "mcp",
        "action": "db.drop_tables",
        "payload": {}
    }
    # Note: AuthorityBundle default in capi.py might allow mcp.
    # But we want to test that a MISSING rule denys.
    response = client.post("/api/v1/capi/execute", json=payload)
    # If it fails with 403 and reason NO_EXPLICIT_ALLOW_RULE, it's working
    assert response.status_code == 403
    data = response.json()
    assert data["detail"]["phase"] == 2
    assert "NO_EXPLICIT_ALLOW_RULE" in data["detail"]["reason"] or "POLICIES_CONSTRUCT_DENY" in data["detail"]["reason"]

@pytest.mark.asyncio
async def test_terminal_governance_wiring():
    """Test that the /terminal/run endpoint is now governed."""
    payload = {
        "intent": "rm -rf /",
        "agent_id": "terminal-test-agent",
        "pgl_id": "terminal-test-pgl"
    }
    response = client.post("/api/v1/terminal/run", json=payload)
    # This should be intercepted by Phase 2 (System Veto or No Explicit Allow)
    # or Phase 5 (Human Approval required for destructive actions)
    assert response.status_code == 403
    data = response.json()
    # It should return a cAPI receipt error
    assert data["detail"]["error"] == "cAPI_VETO_ENGAGED"
