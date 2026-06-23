import os
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["REDIS_ENABLED"] = "False"

import backend.db.models  # Ensure all models are loaded
import pytest
from fastapi.testclient import TestClient

from backend.apps.api.main import app
from backend.core.database.database import Base, engine
from backend.db.models.benchmarks import NexusBenchmarkRun, AgentPrivilege

@pytest.fixture
def test_client():
    return TestClient(app)

@pytest.mark.asyncio
async def test_dynamic_revocation_hard_floors(test_client):
    # Setup sqlite tables
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: Base.metadata.create_all(
            bind=sync_conn,
            tables=[
                NexusBenchmarkRun.__table__,
                AgentPrivilege.__table__,
            ]
        ))
        
    # Test 1: Passing benchmark
    payload_pass = {
        "agent_id": "test-agent-01",
        "provider": "openai",
        "policy_adherence_score": 95.0,
        "evidence_integrity_score": 98.0,
        "latency_ms": 500,
        "cost_efficiency_score": 90.0
    }
    
    resp = test_client.post("/api/v1/nexus/benchmark/evaluate", json=payload_pass)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "passed"
    assert data["privilege_revoked"] is False
    
    # Check privilege
    resp_priv = test_client.get("/api/v1/nexus/agent/test-agent-01/privilege")
    assert resp_priv.status_code == 200
    assert resp_priv.json()["is_active"] is True
    
    # Test 2: Failing benchmark due to composite score < 70
    payload_fail_composite = {
        "agent_id": "test-agent-02",
        "provider": "anthropic",
        "policy_adherence_score": 85.0,
        "evidence_integrity_score": 95.0,
        "latency_ms": 5000, # Very high latency ruins composite score
        "cost_efficiency_score": 10.0
    }
    
    resp = test_client.post("/api/v1/nexus/benchmark/evaluate", json=payload_fail_composite)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "revoked"
    assert data["privilege_revoked"] is True
    assert "Composite score" in data["message"]
    
    # Check privilege
    resp_priv = test_client.get("/api/v1/nexus/agent/test-agent-02/privilege")
    assert resp_priv.status_code == 200
    assert resp_priv.json()["is_active"] is False
    
    # Test 3: Failing benchmark due to policy adherence floor < 80
    payload_fail_policy = {
        "agent_id": "test-agent-03",
        "provider": "gemini",
        "policy_adherence_score": 75.0, # Below 80!
        "evidence_integrity_score": 100.0,
        "latency_ms": 200,
        "cost_efficiency_score": 100.0
    }
    
    resp = test_client.post("/api/v1/nexus/benchmark/evaluate", json=payload_fail_policy)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "revoked"
    assert data["privilege_revoked"] is True
    assert "Policy adherence score" in data["message"]
    
    # Check privilege
    resp_priv = test_client.get("/api/v1/nexus/agent/test-agent-03/privilege")
    assert resp_priv.status_code == 200
    assert resp_priv.json()["is_active"] is False

    # Test 4: Failing benchmark due to evidence integrity floor < 90
    payload_fail_evidence = {
        "agent_id": "test-agent-04",
        "provider": "local",
        "policy_adherence_score": 100.0,
        "evidence_integrity_score": 85.0, # Below 90!
        "latency_ms": 200,
        "cost_efficiency_score": 100.0
    }
    
    resp = test_client.post("/api/v1/nexus/benchmark/evaluate", json=payload_fail_evidence)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "revoked"
    assert data["privilege_revoked"] is True
    assert "Evidence integrity score" in data["message"]
    
    # Check privilege
    resp_priv = test_client.get("/api/v1/nexus/agent/test-agent-04/privilege")
    assert resp_priv.status_code == 200
    assert resp_priv.json()["is_active"] is False
