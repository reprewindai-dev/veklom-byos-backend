import pytest
import uuid
from fastapi.testclient import TestClient

from backend.apps.api.main import app
from backend.core.config.settings import settings
from backend.core.database.database import async_session, engine, Base
from backend.db.models.security import AuditLog, SecurityEvent
from backend.db.models.run import VeklomRun
from backend.db.models.user import User

from unittest.mock import AsyncMock, patch
from backend.services.orchestrator import RunOrchestrator

@pytest.mark.asyncio
@patch.object(RunOrchestrator, "create_run", new_callable=AsyncMock)
async def test_edge_connector_webhook_ingest(mock_create_run):
    # Setup Edge API key and database
    original_key = settings.EDGE_API_KEY
    settings.EDGE_API_KEY = "test_edge_secret_key_123"
    
    # Initialize edge and security database tables
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: Base.metadata.create_all(
            bind=sync_conn,
            tables=[AuditLog.__table__, SecurityEvent.__table__]
        ))
        
    client = TestClient(app)
    ws_id = str(uuid.uuid4())
    
    try:
        # 1. Reject missing API key with 401
        payload = {
            "source_protocol": "webhook",
            "source_system": "legacy-hvac-controller",
            "workspace_id": ws_id,
            "signal_type": "temperature_alert",
            "payload": {"value": 85.4, "status": "fail"},
            "severity": "critical"
        }
        
        response = client.post("/api/v1/edge/input/webhook", json=payload)
        assert response.status_code == 401
        
        # 2. Reject incorrect API key with 403
        response = client.post(
            "/api/v1/edge/input/webhook",
            json=payload,
            headers={"X-Edge-Api-Key": "wrong_key"}
        )
        assert response.status_code == 403
        
        # 3. Reject invalid protocol with 400
        invalid_protocol_payload = dict(payload, source_protocol="invalid_protocol")
        response = client.post(
            "/api/v1/edge/input/webhook",
            json=invalid_protocol_payload,
            headers={"X-Edge-Api-Key": settings.EDGE_API_KEY}
        )
        assert response.status_code == 400
        assert "Unsupported protocol" in response.json()["detail"]

        # 4. Accept valid critical payload with 200 and return canonical edge message
        response = client.post(
            "/api/v1/edge/input/webhook",
            json=payload,
            headers={"X-Edge-Api-Key": settings.EDGE_API_KEY}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["source_protocol"] == "webhook"
        assert data["source_system"] == "legacy-hvac-controller"
        assert data["normalized_fields"]["warning"] is True
        assert data["normalized_fields"]["metric_value"] == 85.4
        
        # 5. Verify database insertions for critical event (should log to AuditLog, SecurityEvent, and VeklomRun)
        async with async_session() as db:
            from sqlalchemy import select
            
            # Check AuditLog
            res = await db.execute(select(AuditLog).where(AuditLog.workspace_id == ws_id))
            logs = res.scalars().all()
            assert len(logs) == 1
            assert "edge.ingest.webhook" in logs[0].action
            
            # Check SecurityEvent
            res = await db.execute(select(SecurityEvent).where(SecurityEvent.workspace_id == ws_id))
            events = res.scalars().all()
            assert len(events) == 1
            assert events[0].severity == "critical"
            
            # Check VeklomRun routing via Mock
            assert mock_create_run.call_count == 1
            call_args = mock_create_run.call_args[1]
            assert call_args["workspace_id"] == ws_id
            assert "legacy industrial edge signal" in call_args["intent"]["goal"]
            
        print("Edge connector webhook ingestion test completed successfully!")
        
    finally:
        settings.EDGE_API_KEY = original_key


@pytest.mark.asyncio
async def test_connectors_status():
    original_key = settings.EDGE_API_KEY
    settings.EDGE_API_KEY = "test_edge_secret_key_123"
    
    client = TestClient(app)
    try:
        response = client.get(
            "/api/v1/edge/connectors/status",
            headers={"X-Edge-Api-Key": settings.EDGE_API_KEY}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["webhook_connector"]["status"] == "active"
        assert data["snmp_connector"]["status"] == "disabled"
        assert data["modbus_connector"]["status"] == "disabled"
        
        print("Connectors status query test completed successfully!")
    finally:
        settings.EDGE_API_KEY = original_key
