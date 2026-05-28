import pytest
import hmac
import hashlib
import json
import uuid
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from backend.apps.api.main import app
from backend.core.config.settings import settings
from backend.core.database.database import async_session, engine, Base
from backend.db.models.billing import Order, Ledger, WebhookReceipt, ReconFinding, WebhookDeadLetter
from backend.db.models.user import User
from backend.core.security.auth import create_access_token
from backend.core.services.posthog_client import posthog_service

@pytest.mark.asyncio
async def test_webhook_e2e():
    # Setup test secret
    original_secret = settings.WEBHOOK_SECRET
    settings.WEBHOOK_SECRET = "test_webhook_secret_key_123"
    
    # 0. Initialize database tables (only payment ones to avoid postgres JSONB dependency)
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: Base.metadata.create_all(
            bind=sync_conn,
            tables=[Order.__table__, Ledger.__table__, WebhookReceipt.__table__]
        ))
        
    # Track posthog calls
    posthog_calls = []
    def mock_capture(distinct_id, event, properties=None, groups=None):
        posthog_calls.append({
            "distinct_id": distinct_id,
            "event": event,
            "properties": properties
        })
    original_capture = posthog_service.capture
    posthog_service.capture = mock_capture
    posthog_service.enabled = True
    
    try:
        order_id = f"test_order_{uuid.uuid4()}"
        tx_hash = f"0x{uuid.uuid4().hex}"
        user_id = f"user_{uuid.uuid4().hex[:8]}"
        
        # 1. Create a pending order in database
        async with async_session() as db:
            order = Order(
                order_id=order_id,
                amount=100.0,
                currency="USD",
                user_id=user_id,
                workspace_id="test_workspace_id_123",
                status="pending"
            )
            db.add(order)
            await db.commit()
            
        payload = {
            "type": "tx_confirmed",
            "tx_hash": tx_hash,
            "order_id": order_id,
            "confirmations": 1,
            "amount": 100.0
        }
        payload_bytes = json.dumps(payload).encode()
        
        # Calculate valid signature
        signature = "sha256=" + hmac.new(
            settings.WEBHOOK_SECRET.encode(),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()
        
        idempotency_key = f"idem_{uuid.uuid4()}"
        
        # 2. Test valid webhook HMAC returns 200
        client = TestClient(app)
        response = client.post(
            "/api/v1/webhook/payment",
            content=payload_bytes,
            headers={
                "X-Signature": signature,
                "X-Idempotency-Key": idempotency_key
            }
        )
            
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["idempotent"] is False
        
        # Verify DB updates
        async with async_session() as db:
            # Order should be confirmed
            from sqlalchemy import select
            res = await db.execute(select(Order).where(Order.order_id == order_id))
            db_order = res.scalar_one()
            assert db_order.status == "confirmed"
            assert db_order.tx_hash == tx_hash
            
            # Ledger should have exactly one entry (writes exactly once)
            res = await db.execute(select(Ledger).where(Ledger.order_id == order_id))
            db_ledger = res.scalars().all()
            assert len(db_ledger) == 1
            assert db_ledger[0].tx_hash == tx_hash
            assert db_ledger[0].amount == 100.0
            
        # 3. Test invalid webhook HMAC returns 401
        invalid_signature = "sha256=wrongsignaturehere"
        response = client.post(
            "/api/v1/webhook/payment",
            content=payload_bytes,
            headers={
                "X-Signature": invalid_signature,
                "X-Idempotency-Key": f"idem_new_{uuid.uuid4()}"
            }
        )
        assert response.status_code == 401
        
        # 4. Test idempotency key replay protection
        # Send again with same idempotency key and same body
        response = client.post(
            "/api/v1/webhook/payment",
            content=payload_bytes,
            headers={
                "X-Signature": signature,
                "X-Idempotency-Key": idempotency_key
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["idempotent"] is True
        
        # Verify ledger still has exactly one entry (idempotency key protection)
        async with async_session() as db:
            res = await db.execute(select(Ledger).where(Ledger.order_id == order_id))
            db_ledger = res.scalars().all()
            assert len(db_ledger) == 1
            
        # 5. Verify PostHog events appear
        assert len(posthog_calls) == 1
        assert posthog_calls[0]["event"] == "payment_confirmed"
        assert posthog_calls[0]["distinct_id"] == user_id
        assert posthog_calls[0]["properties"]["order_id"] == order_id
        assert posthog_calls[0]["properties"]["tx_hash"] == tx_hash
        print("Webhook E2E Tests completed successfully!")
        
    finally:
        settings.WEBHOOK_SECRET = original_secret
        posthog_service.capture = original_capture


@pytest.mark.asyncio
async def test_admin_endpoints_e2e():
    # 0. Initialize database tables
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: Base.metadata.create_all(
            bind=sync_conn,
            tables=[User.__table__, ReconFinding.__table__, WebhookDeadLetter.__table__]
        ))
        
    admin_user_id = f"admin_{uuid.uuid4().hex[:8]}"
    
    # 1. Seed an admin user
    async with async_session() as db:
        admin_user = User(
            id=admin_user_id,
            email="admin_test@veklom.com",
            hashed_password="hashedpassword123",
            role="admin",
            is_active=True,
            status="active",
            workspace_id="test_workspace_id_123"
        )
        db.add(admin_user)
        await db.commit()
        
    # Generate admin token
    token = create_access_token({"sub": admin_user_id, "role": "admin"})
    
    client = TestClient(app)
    
    # 2. Test admin endpoints with auth
    # Test recon_findings
    response = client.get(
        "/api/v1/admin/recon_findings",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    findings = response.json()
    assert isinstance(findings, list)
    
    # Test webhook_dead_letter
    response = client.get(
        "/api/v1/admin/webhook_dead_letter",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    dead_letters = response.json()
    assert isinstance(dead_letters, list)
    
    # 3. Test without auth returns 401
    response = client.get("/api/v1/admin/recon_findings")
    assert response.status_code == 401
    
    print("Admin API E2E Tests completed successfully!")
