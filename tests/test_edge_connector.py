import pytest
import uuid
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from backend.apps.api.main import app
from backend.core.config.settings import settings
from backend.core.database.database import async_session, engine, Base
from backend.db.models.security import AuditLog, SecurityEvent
from backend.db.models.run import VeklomRun
from backend.services.orchestrator import RunOrchestrator

@pytest.mark.asyncio
async def test_edge_connector_comprehensive():
    original_key = settings.EDGE_API_KEY
    settings.EDGE_API_KEY = "test_edge_secret_key_123"
    
    # Initialize edge database tables
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: Base.metadata.create_all(
            bind=sync_conn,
            tables=[AuditLog.__table__, SecurityEvent.__table__]
        ))
        
    client = TestClient(app)
    ws_id = str(uuid.uuid4())
    
    try:
        # Assertion 1: App boots & Assertion 2: /openapi.json includes /api/v1/edge/input/webhook
        openapi_resp = client.get("/openapi.json")
        assert openapi_resp.status_code == 200
        schema = openapi_resp.json()
        assert "/api/v1/edge/input/webhook" in schema["paths"]

        # Request payload setup
        payload = {
            "source_protocol": "webhook",
            "source_system": "legacy-hvac-controller",
            "workspace_id": ws_id,
            "signal_type": "temperature_alert",
            "payload": {"value": 85.4, "status": "fail"},
            "severity": "critical"
        }
        
        # Assertion 3: Missing auth is rejected with 401
        response = client.post("/api/v1/edge/input/webhook", json=payload)
        assert response.status_code == 401
        
        # Assertion 4: Invalid X-Edge-Api-Key is rejected with 403
        response = client.post(
            "/api/v1/edge/input/webhook",
            json=payload,
            headers={"X-Edge-Api-Key": "wrong_key"}
        )
        assert response.status_code == 403
        
        # Assertion 5: Missing EDGE_API_KEY fails closed with 503
        with patch.object(settings, "EDGE_API_KEY", ""):
            response = client.post(
                "/api/v1/edge/input/webhook",
                json=payload,
                headers={"X-Edge-Api-Key": "test_edge_secret_key_123"}
            )
            assert response.status_code == 503
            assert "authentication is not configured" in response.json()["detail"]

        # Assertion 6: Malformed payload returns 422 or 400 validation error
        malformed_payload = {
            "source_protocol": "webhook",
            "source_system": "legacy-hvac-controller"
            # missing signal_type and payload
        }
        response = client.post(
            "/api/v1/edge/input/webhook",
            json=malformed_payload,
            headers={"X-Edge-Api-Key": settings.EDGE_API_KEY}
        )
        assert response.status_code in (400, 422)

        # Assertion 7: Unsupported protocol is rejected with 422/400
        unsupported_protocol_payload = dict(payload, source_protocol="invalid_protocol")
        response = client.post(
            "/api/v1/edge/input/webhook",
            json=unsupported_protocol_payload,
            headers={"X-Edge-Api-Key": settings.EDGE_API_KEY}
        )
        assert response.status_code == 422
        assert "Unsupported protocol" in response.json()["detail"]

        # Assertion 7.2: Invalid severity is rejected with 422/400
        unsupported_severity_payload = dict(payload, severity="super_critical")
        response = client.post(
            "/api/v1/edge/input/webhook",
            json=unsupported_severity_payload,
            headers={"X-Edge-Api-Key": settings.EDGE_API_KEY}
        )
        assert response.status_code == 422
        assert "Unsupported severity" in response.json()["detail"]

        # Assertion 8, 9, 10, 11: Valid webhook event returns accepted=True, normalized=True, missing timestamp/correlation gets generated
        with patch.object(RunOrchestrator, "create_run", new_callable=AsyncMock) as mock_create_run:
            response = client.post(
                "/api/v1/edge/input/webhook",
                json=payload,
                headers={"X-Edge-Api-Key": settings.EDGE_API_KEY}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["accepted"] is True
            assert data["normalized"] is True
            assert data["event_id"] != ""
            assert data["correlation_id"].startswith("corr_")
            assert data["audit_status"] == "persisted"
            assert data["security_event_status"] == "persisted"
            assert data["routing_status"] == "routed"
            assert len(data["warnings"]) == 0

            # Verify VeklomRun routing occurred
            assert mock_create_run.call_count == 1
            call_args = mock_create_run.call_args[1]
            assert call_args["workspace_id"] == ws_id
            assert "legacy industrial edge signal" in call_args["intent"]["goal"]

        # Assertion 12: No queue/routing is invented when no real queue exists (represented by low severity)
        low_severity_payload = dict(payload, severity="info")
        response = client.post(
            "/api/v1/edge/input/webhook",
            json=low_severity_payload,
            headers={"X-Edge-Api-Key": settings.EDGE_API_KEY}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["routing_status"] == "logged_only" # Safely not routed for info severity

        # Verify DB insertions for high severity event (from earlier test)
        async with async_session() as db:
            from sqlalchemy import select
            # Check AuditLog
            res = await db.execute(select(AuditLog).where(AuditLog.workspace_id == ws_id))
            logs = res.scalars().all()
            assert len(logs) >= 1
            
            # Check SecurityEvent
            res = await db.execute(select(SecurityEvent).where(SecurityEvent.workspace_id == ws_id))
            events = res.scalars().all()
            assert len(events) >= 1

    finally:
        settings.EDGE_API_KEY = original_key


@pytest.mark.asyncio
async def test_connectors_status_and_stubs():
    original_key = settings.EDGE_API_KEY
    settings.EDGE_API_KEY = "test_edge_secret_key_123"
    
    client = TestClient(app)
    try:
        # Assertion 13: Protocol stubs are disabled by default
        response = client.get(
            "/api/v1/edge/connectors/status",
            headers={"X-Edge-Api-Key": settings.EDGE_API_KEY}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["webhook_connector"]["status"] == "active"
        assert data["webhook_connector"]["write_control"] is False
        assert data["webhook_connector"]["ingestion_only"] is True
        assert data["webhook_connector"]["no_network_polling_starts_automatically"] is True
        
        # Stubs disabled by default: supported=False
        assert data["snmp_connector"]["status"] == "disabled"
        assert data["snmp_connector"]["supported"] is False
        assert data["modbus_connector"]["status"] == "disabled"
        assert data["modbus_connector"]["supported"] is False
        assert data["opc_ua_connector"]["status"] == "disabled"
        assert data["opc_ua_connector"]["supported"] is False
        assert data["mqtt_connector"]["status"] == "disabled"
        assert data["mqtt_connector"]["supported"] is False
        
    finally:
        settings.EDGE_API_KEY = original_key
