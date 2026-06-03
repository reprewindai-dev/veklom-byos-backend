import os
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["REDIS_ENABLED"] = "False"

import pytest
import uuid
from fastapi.testclient import TestClient
from sqlalchemy import select
from unittest.mock import patch

from backend.apps.api.main import app
from backend.core.database.database import async_session, engine, Base
from backend.db.models.security import AuditLog
from backend.db.models.user import User

@pytest.fixture
def mock_user():
    class MockUser:
        id = "test-operator-123"
        workspace_id = "test-workspace-abc"
        role = "OWNER"
        plan = "pro"
    return MockUser()

@pytest.mark.asyncio
async def test_fax_connector_workflow(mock_user):
    # Initialize the database schema for the test
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: Base.metadata.create_all(
            bind=sync_conn,
            tables=[AuditLog.__table__]
        ))

    client = TestClient(app)

    # Mock authentication dependency
    from backend.core.security.auth import get_current_user
    app.dependency_overrides[get_current_user] = lambda: mock_user

    # Import settings to get the secret for signing
    from backend.core.config.settings import settings

    try:
        # 1. Ingest Inbound Fax via Webhook
        inbound_payload = {
            "sender_number": "+15550192",
            "receiver_number": "+18005550100",
            "document_url": "https://storage.veklom.com/faxes/patient_clinical_intake_form.pdf"
        }
        
        # Test 1a: Missing key (header) -> 401 Unauthorized
        response_missing = client.post("/api/v1/connectors/fax/inbound", json=inbound_payload)
        assert response_missing.status_code == 401

        # Test 1b: Invalid key (header) -> 403 Forbidden
        response_invalid = client.post(
            "/api/v1/connectors/fax/inbound", 
            json=inbound_payload, 
            headers={"X-Fax-Signature": "invalid_secret_key"}
        )
        assert response_invalid.status_code == 403

        # Test 1c: Malformed payload with valid key -> 422 Unprocessable Entity (FastAPI validation)
        response_malformed = client.post(
            "/api/v1/connectors/fax/inbound", 
            json={"sender_number": "only_one_field"}, 
            headers={"X-Fax-Signature": settings.FAX_WEBHOOK_SECRET}
        )
        assert response_malformed.status_code in (400, 422)

        # Test 1d: Valid signed webhook -> 201 Created
        response = client.post(
            "/api/v1/connectors/fax/inbound", 
            json=inbound_payload,
            headers={"X-Fax-Signature": settings.FAX_WEBHOOK_SECRET}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["fax_id"].startswith("fax_in_")
        assert data["status"] == "queued"
        assert data["sender_number"] == "+15550192"
        assert "PATIENT intake form" in data["ocr_text"]
        assert data["classification"] == "PHI_CLINICAL_INTAKE"
        assert "Healthcare" in data["industry_context"]
        assert "evidence_id" in data
        
        fax_in_id = data["fax_id"]

        # Verify Audit Log entry created for the inbound fax
        async with async_session() as db:
            res = await db.execute(select(AuditLog).where(AuditLog.resource_id == fax_in_id))
            audit_entry = res.scalar_one_or_none()
            assert audit_entry is not None
            assert audit_entry.action == "CONNECTORS_FAX_INGEST"
            assert audit_entry.details["classification"] == "PHI_CLINICAL_INTAKE"

        # 2. Trigger Outbound Fax (Approval Required by Default)
        outbound_payload = {
            "recipient_number": "+15550999",
            "sender_number": "+18005550100",
            "document_url": "https://storage.veklom.com/faxes/court_legal_brief_final.pdf",
            "require_approval": True
        }
        
        response = client.post("/api/v1/connectors/fax/send", json=outbound_payload)
        assert response.status_code == 201
        data = response.json()
        assert data["fax_id"].startswith("fax_out_")
        assert data["status"] == "pending_approval"
        assert "IN THE DISTRICT COURT" in data["ocr_text"]
        assert data["classification"] == "LEGAL_COURT_FILING"
        assert "Legal Services" in data["industry_context"]
        
        fax_out_id = data["fax_id"]

        # 3. Retrieve Inbox/Queue List
        response = client.get("/api/v1/connectors/fax/inbox")
        assert response.status_code == 200
        inbox = response.json()
        assert len(inbox) >= 2
        
        # Verify both faxes are in the inbox
        fax_ids = [f["fax_id"] for f in inbox]
        assert fax_in_id in fax_ids
        assert fax_out_id in fax_ids

        # 4. Approve Pending Outbound Fax
        approval_payload = {
            "approved": True,
            "reviewer_notes": "All legal risk gates verified. Releasing document."
        }
        
        response = client.post(f"/api/v1/connectors/fax/approve/{fax_out_id}", json=approval_payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "sent"
        assert data["approved_by"] == mock_user.id
        assert data["approval_notes"] == "All legal risk gates verified. Releasing document."

        # Verify Audit Log entry created for the approval
        async with async_session() as db:
            res = await db.execute(select(AuditLog).where(
                AuditLog.resource_id == fax_out_id,
                AuditLog.action == "CONNECTORS_FAX_APPROVAL"
            ))
            audit_entry = res.scalar_one_or_none()
            assert audit_entry is not None
            assert audit_entry.details["decision"] == "approved"
            assert audit_entry.details["reviewer"] == mock_user.id

        # 5. Fetch Single Fax Detail
        response = client.get(f"/api/v1/connectors/fax/{fax_in_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["fax_id"] == fax_in_id
        assert data["sender_number"] == "+15550192"

    finally:
        # Clean up dependency overrides
        app.dependency_overrides.clear()
