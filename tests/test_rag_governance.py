import os
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["REDIS_ENABLED"] = "False"

import pytest
from fastapi.testclient import TestClient
from backend.apps.api.main import app
from backend.core.database.database import Base, engine
from backend.db.models.rag import AgentMemoryStore, DocumentChunk
from backend.db.models.benchmarks import AgentPrivilege
from backend.db.models.pgl import PGLLedgerEvent

@pytest.fixture
def test_client():
    return TestClient(app)

@pytest.mark.asyncio
async def test_rag_pgl_and_seked_governance(test_client):
    # Setup sqlite tables
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: Base.metadata.create_all(
            bind=sync_conn,
            tables=[
                AgentMemoryStore.__table__,
                DocumentChunk.__table__,
                AgentPrivilege.__table__,
                PGLLedgerEvent.__table__
            ]
        ))
        
    # Scenario 1: Missing PGL ID should fail
    payload_no_pgl = {
        "agent_id": "test-agent-01",
        "pgl_id": "",
        "tenant_id": "tenant-001",
        "content": "Secret memory",
        "embedding": [0.1] * 1536
    }
    resp = test_client.post("/api/v1/rag/memory/store", json=payload_no_pgl)
    assert resp.status_code == 401
    assert "MISSING_PGL_SIGNATURE" in resp.json()["detail"]
    
    # Scenario 2: Valid PGL ID (using demo id for bypass) but active privileges
    # Note: We must create an active privilege record or it defaults to active
    payload_valid = {
        "agent_id": "test-agent-01",
        "pgl_id": "terminal-demo-pgl-id",
        "tenant_id": "tenant-001",
        "content": "This is a legitimate memory",
        "embedding": [0.1] * 1536
    }
    resp = test_client.post("/api/v1/rag/memory/store", json=payload_valid)
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"
    
    # Scenario 3: Agent is revoked by SEKED
    # We simulate a revoked agent by explicitly creating a revoked privilege
    from backend.core.database.database import async_session
    async with async_session() as session:
        priv = AgentPrivilege(agent_id="test-agent-bad", provider="openai", status="revoked", revocation_reason="Failed benchmark")
        session.add(priv)
        await session.commit()
        
    payload_revoked = {
        "agent_id": "test-agent-bad",
        "pgl_id": "terminal-demo-pgl-id",
        "tenant_id": "tenant-001",
        "content": "Malicious attempt to read memory",
        "query_embedding": [0.1] * 1536
    }
    resp = test_client.post("/api/v1/rag/memory/retrieve", json=payload_revoked)
    assert resp.status_code == 403
    assert "revoked privileges" in resp.json()["detail"]
