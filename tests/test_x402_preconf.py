import os
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["REDIS_ENABLED"] = "False"

import pytest
import uuid
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from unittest.mock import patch

from backend.apps.api.main import app
from backend.core.config.settings import settings
from backend.core.database.database import async_session, engine, Base
from backend.db.models.security import AuditLog
from backend.apps.api.routers.x402 import get_treasury_address, resolve_basename
from sqlalchemy import select

@pytest.mark.asyncio
async def test_x402_preconf_features():
    # Save settings to restore
    original_mode = settings.X402_TEST_PROOF_MODE
    original_treasury = os.environ.get("VEKLOM_TREASURY_ADDRESS", "")
    
    settings.X402_TEST_PROOF_MODE = True
    os.environ["VEKLOM_TREASURY_ADDRESS"] = "veklom.base.eth"

    # Initialize SQLite db schema for testing AuditLogs
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: Base.metadata.create_all(
            bind=sync_conn,
            tables=[AuditLog.__table__]
        ))

    client = TestClient(app)

    try:
        # 1. BASENAMES RESOLUTION TEST
        # Verify that get_treasury_address resolves veklom.base.eth to the mock treasury address
        treasury = get_treasury_address()
        assert treasury == "0xCC34553b4e6332ffb9C1b61E22436ACA53113D1d"

        # 2. BASE COMMERCE PAYMENTS PROTOCOL (MULTI-STAGE OPERATIONS)
        # A. Authorize
        auth_req = {
            "amount": 0.05,
            "payer": "0x1234567890123456789012345678901234567890",
            "pay_to": "veklom.base.eth",
            "reference_id": "shopify_order_112233"
        }
        res_auth = client.post("/api/v1/x402/payment/authorize", json=auth_req)
        assert res_auth.status_code == 200
        auth_data = res_auth.json()
        assert auth_data["status"] == "authorized"
        assert auth_data["payment_id"].startswith("xpay_auth_")
        assert auth_data["pay_to"] == "0xCC34553b4e6332ffb9C1b61E22436ACA53113D1d"
        payment_id = auth_data["payment_id"]

        # B. Capture
        capture_req = {
            "payment_id": payment_id,
            "amount": 0.05
        }
        res_cap = client.post("/api/v1/x402/payment/capture", json=capture_req)
        assert res_cap.status_code == 200
        cap_data = res_cap.json()
        assert cap_data["status"] == "captured"
        assert cap_data["amount"] == 0.05
        assert cap_data["tx_hash"].startswith("0x_mock_capture_")

        # C. Refund
        refund_req = {
            "payment_id": payment_id,
            "amount": 0.02
        }
        res_ref = client.post("/api/v1/x402/payment/refund", json=refund_req)
        print("REFUND RESPONSE STATUS:", res_ref.status_code)
        print("REFUND RESPONSE JSON:", res_ref.json())
        assert res_ref.status_code == 200
        ref_data = res_ref.json()
        assert ref_data["status"] == "refunded"
        assert ref_data["amount"] == pytest.approx(0.03) # 0.05 - 0.02 remaining
        assert ref_data["refunded_amount"] == pytest.approx(0.02)

        # D. Void Authorization
        res_auth2 = client.post("/api/v1/x402/payment/authorize", json=auth_req)
        payment_id2 = res_auth2.json()["payment_id"]
        res_void = client.post("/api/v1/x402/payment/void", json={"payment_id": payment_id2})
        assert res_void.status_code == 200
        assert res_void.json()["status"] == "voided"

        # E. Reclaim Escrow
        res_auth3 = client.post("/api/v1/x402/payment/authorize", json=auth_req)
        payment_id3 = res_auth3.json()["payment_id"]
        # Capture it first
        client.post("/api/v1/x402/payment/capture", json={"payment_id": payment_id3})
        # Reclaim it
        res_reclaim = client.post(
            "/api/v1/x402/payment/reclaim",
            json={"payment_id": payment_id3, "recipient": "0xbuyeraddress"}
        )
        assert res_reclaim.status_code == 200
        assert res_reclaim.json()["status"] == "reclaimed"
        assert res_reclaim.json()["pay_to"] == "0xbuyeraddress"

        # F. Direct Charge
        charge_req = {
            "amount": 0.025,
            "payer": "0x1234567890123456789012345678901234567890",
            "pay_to": "veklom.base",
            "tx_hash": "0x1111111111111111111111111111111111111111111111111111111111111111"
        }
        res_chg = client.post("/api/v1/x402/payment/charge", json=charge_req)
        assert res_chg.status_code == 200
        assert res_chg.json()["status"] == "charged"
        assert res_chg.json()["payment_id"].startswith("xpay_chg_")

        # 3. MIDDLEWARE INTEGRATION TEST (xpay_ bypass)
        # Create an authorized payment matching the exact cost of protected route (0.025 USDC)
        route_cost_auth = {
            "amount": 0.025,
            "payer": "0xpayer",
            "pay_to": "veklom.base.eth"
        }
        res_auth_route = client.post("/api/v1/x402/payment/authorize", json=route_cost_auth)
        route_payment_id = res_auth_route.json()["payment_id"]

        # Call protected endpoint with valid proof token -> Success (200)
        test_payload = {"messages": [{"role": "user", "content": "test"}]}
        res_route = client.post(
            "/api/v1/x402/protected-test",
            json=test_payload,
            headers={"X-Payment-Proof": route_payment_id}
        )
        assert res_route.status_code == 200
        assert "X-Veklom-Receipt-ID" in res_route.headers

        # Replay: Call again with same token -> Rejected (402 replay_detected)
        res_route_replay = client.post(
            "/api/v1/x402/protected-test",
            json=test_payload,
            headers={"X-Payment-Proof": route_payment_id}
        )
        assert res_route_replay.status_code == 402
        assert res_route_replay.json()["detail"] in ("replay_detected", "replay_storage_unavailable")

        # 4. FLASHBLOCKS SETTING TEST
        assert settings.FLASHBLOCKS_RPC_URL == "https://mainnet.base.org"

    finally:
        settings.X402_TEST_PROOF_MODE = original_mode
        if original_treasury:
            os.environ["VEKLOM_TREASURY_ADDRESS"] = original_treasury
        else:
            os.environ.pop("VEKLOM_TREASURY_ADDRESS", None)
