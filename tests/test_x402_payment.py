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
from sqlalchemy import select

@pytest.mark.asyncio
async def test_x402_comprehensive():
    import base64
    import json

    # Store settings to restore later
    original_mode = settings.X402_TEST_PROOF_MODE
    original_treasury = os.environ.get("VEKLOM_TREASURY_ADDRESS", "")
    if not original_treasury or original_treasury == "0x0000000000000000000000000000000000000001":
        os.environ["VEKLOM_TREASURY_ADDRESS"] = "0xCC34553b4e6332ffb9C1b61E22436ACA53113D1d"

    # Ensure tables are initialized for testing receipts
    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: Base.metadata.create_all(
            bind=sync_conn,
            tables=[AuditLog.__table__]
        ))

    client = TestClient(app)
    ws_id = str(uuid.uuid4())

    try:
        # A. DISCOVERY ASSERTIONS
        # Assertion 1: both /.well-known/x402 and /.well-known/x402.json return identical 200 and application/json Content-Type
        disc_resp = client.get("/.well-known/x402.json")
        assert disc_resp.status_code == 200
        assert "application/json" in disc_resp.headers.get("content-type", "")
        disc_data = disc_resp.json()

        disc_resp_unsuffixed = client.get("/.well-known/x402")
        assert disc_resp_unsuffixed.status_code == 200
        assert "application/json" in disc_resp_unsuffixed.headers.get("content-type", "")
        assert disc_data == disc_resp_unsuffixed.json()

        assert "enabled" in disc_data
        assert disc_data["x402_version"] == "2.0.0"
        assert "replay_protection" in disc_data
        assert disc_data["proof_header_name"] == "payment-signature"

        config_resp = client.get("/api/v1/x402/config")
        assert config_resp.status_code == 200
        config_data = config_resp.json()
        assert config_data["enabled"] is True
        assert config_data["chain_id"] == 8453
        assert config_data["x402_version"] == "2.0.0"
        assert config_data["proof_header_name"] == "payment-signature"
        assert config_data["environment_mode"] == settings.APP_ENV

        # Assertion 2: Discovery with missing config sets enabled=False
        with patch.dict(os.environ, {"VEKLOM_TREASURY_ADDRESS": ""}):
            config_resp = client.get("/api/v1/x402/config")
            assert config_resp.json()["enabled"] is False
            assert "VEKLOM_TREASURY_ADDRESS" in config_resp.json()["missing_config"]

        # B. CHALLENGE ASSERTIONS
        # Assertion 3: Unpaid protected request returns HTTP 402 with scoped challenge JSON
        test_payload = {
            "messages": [{"role": "user", "content": "test message"}]
        }
        response = client.post("/api/v1/x402/protected-test", json=test_payload)
        assert response.status_code == 402
        challenge = response.json()
        assert challenge["error"] == "payment_required"
        assert challenge["x402_version"] == "2.0.0"
        assert "challenge_id" in challenge
        assert "nonce" in challenge
        assert challenge["amount"] == 0.025
        assert challenge["currency"] == "USDC"
        assert challenge["network"] == "base"
        assert challenge["route"] == "/api/v1/x402/protected-test"
        assert challenge["method"] == "POST"
        assert "expires_at" in challenge
        assert challenge["proof_header_name"] == "payment-signature"

        # Assertion 3.2: 402 Headers exist on response
        assert response.headers.get("X-Payment-Required") == "true"
        assert "X-Payment-Challenge-ID" in response.headers
        assert "X-Payment-Nonce" in response.headers

        # CDP v2 Compliant Headers Assertion
        assert "payment-required" in response.headers
        assert "Payment-Required" in response.headers
        v2_b64 = response.headers["payment-required"]
        v2_payload = json.loads(base64.b64decode(v2_b64).decode("utf-8"))
        assert v2_payload["x402Version"] == "2.0.0"
        assert "resource" in v2_payload
        assert v2_payload["resource"]["url"] == "https://api.veklom.com/api/v1/x402/protected-test"
        assert len(v2_payload["accepts"]) == 1
        accepts = v2_payload["accepts"][0]
        assert accepts["scheme"] == "exact"
        assert accepts["network"] == "eip155:8453"
        assert accepts["amount"] == "25000"  # 0.025 * 1_000_000
        assert accepts["asset"] == "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
        assert accepts["payTo"] == os.environ["VEKLOM_TREASURY_ADDRESS"]

        # C. PROOF VERIFICATION ASSERTIONS
        # Enable dev test proof mode for validation
        settings.X402_TEST_PROOF_MODE = True

        # Assertion 4: Missing proof is rejected (Already proven via 402 response)
        
        # Assertion 5: Malformed/Invalid proof is rejected using standard payment-signature header
        response = client.post(
            "/api/v1/x402/protected-test",
            json=test_payload,
            headers={"payment-signature": "test_proof_invalid"}
        )
        assert response.status_code == 402
        assert response.json()["detail"] == "invalid_transaction"

        # Assertion 6: Replayed proof is rejected
        valid_proof = f"test_proof_valid_{uuid.uuid4().hex[:8]}"
        
        # Use first time with standard header -> Success (200)
        response = client.post(
            "/api/v1/x402/protected-test",
            json=test_payload,
            headers={"payment-signature": valid_proof}
        )
        assert response.status_code == 200
        assert response.headers.get("X-Payment-Test-Mode") == "true"
        assert "X-Veklom-Receipt-ID" in response.headers
        receipt_id = response.headers["X-Veklom-Receipt-ID"]
        evidence_hash = response.headers["X-Veklom-Evidence-ID"]
        
        # Use second time -> Replay Rejected (402)
        response = client.post(
            "/api/v1/x402/protected-test",
            json=test_payload,
            headers={"payment-signature": valid_proof}
        )
        assert response.status_code == 402
        assert response.json()["detail"] == "replay_detected"

        # D. RECEIPT GENERATION ASSERTIONS
        # Assertion 7: Receipt is persisted in AuditLog
        async with async_session() as db:
            res = await db.execute(select(AuditLog).where(AuditLog.resource_id == receipt_id))
            receipt_log = res.scalar_one_or_none()
            assert receipt_log is not None
            assert receipt_log.action == "x402.receipt.create"
            assert receipt_log.details["persistence_status"] == "persisted"
            assert receipt_log.details["evidence_hash"] == evidence_hash

        # E. EVIDENCE VERIFICATION ASSERTIONS
        # First-Gate Enforcement Assertion: Posting empty payload or invalid JSON to /verify triggers 402 challenge first, NOT 422!
        verify_empty_resp = client.post("/api/v1/x402/verify")
        assert verify_empty_resp.status_code == 402
        assert verify_empty_resp.json()["error"] == "payment_required"

        # Assertion 8: POST /api/v1/x402/verify validates real stored receipt successfully when PAID
        import hashlib
        proof_hash = hashlib.sha256(valid_proof.encode()).hexdigest()
        
        verify_payload = {
            "receipt_id": receipt_id,
            "proof_hash": proof_hash,
            "evidence_hash": evidence_hash
        }
        
        verify_proof_8 = f"test_proof_v8_{uuid.uuid4().hex[:8]}"
        verify_resp = client.post(
            "/api/v1/x402/verify", 
            json=verify_payload,
            headers={"payment-signature": verify_proof_8}
        )
        assert verify_resp.status_code == 200
        verify_data = verify_resp.json()
        assert verify_data["valid"] is True
        assert verify_data["verification_status"] == "verified"
        assert verify_data["evidence_hash_match"] is True
        assert verify_data["proof_hash_match"] is True
        assert verify_data["signature_valid"] is True

        # Assertion 9: Wrong evidence hash fails verification when PAID
        bad_verify_payload = dict(verify_payload, evidence_hash="wrong_hash")
        verify_proof_9 = f"test_proof_v9_{uuid.uuid4().hex[:8]}"
        verify_resp = client.post(
            "/api/v1/x402/verify", 
            json=bad_verify_payload,
            headers={"Payment-Signature": verify_proof_9} # verify title-case version too!
        )
        assert verify_resp.status_code == 200
        verify_data = verify_resp.json()
        assert verify_data["valid"] is False
        assert verify_data["verification_status"] == "mismatched"
        assert "evidence_hash mismatch" in verify_data["reason"]

        # Assertion 10: Querying non-existent receipt fails verification cleanly when PAID
        missing_verify_payload = dict(verify_payload, receipt_id="rcpt_missing123")
        verify_proof_10 = f"test_proof_v10_{uuid.uuid4().hex[:8]}"
        verify_resp = client.post(
            "/api/v1/x402/verify", 
            json=missing_verify_payload,
            headers={"X-Payment-Proof": verify_proof_10} # verify legacy fallback as well!
        )
        assert verify_resp.status_code == 200
        verify_data = verify_resp.json()
        assert verify_data["valid"] is False
        assert verify_data["verification_status"] == "not_found"

        # F. REGRESSION ASSERTIONS
        # Assertion 11: App boots & OpenAPI builds cleanly
        assert client.get("/openapi.json").status_code == 200
        # Assertion 12: Health route is operational and not broken
        assert client.get("/health").status_code == 200

    finally:
        settings.X402_TEST_PROOF_MODE = original_mode
        if original_treasury:
            os.environ["VEKLOM_TREASURY_ADDRESS"] = original_treasury


@pytest.mark.asyncio
async def test_payapi_dynamic_registration_and_parameterized_matching():
    client = TestClient(app)
    
    # 1. Dynamic Route Registration
    register_payload = {
        "name": "Dynamic Niche API",
        "path": "/api/v1/niche-test/{item_id}/process",
        "price": 0.045,
        "description": "A dynamic endpoint listed on PayAPI on-the-fly",
        "openapi_schema_url": "https://api.veklom.com/openapi.json"
    }
    
    resp = client.post("/api/v1/x402/register-api", json=register_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["registered_path"] == "/api/v1/niche-test/{item_id}/process"
    assert data["price_usdc"] == 0.045
    
    # 2. Config Discovery verification
    config_resp = client.get("/api/v1/x402/config")
    assert config_resp.status_code == 200
    config_data = config_resp.json()
    assert "/api/v1/niche-test/{item_id}/process" in config_data["protected_routes"]
    
    # 3. Requesting dynamic path with placeholder match
    response = client.post("/api/v1/niche-test/item_abc123/process", json={})
    assert response.status_code == 402
    challenge = response.json()
    assert challenge["error"] == "payment_required"
    assert challenge["amount"] == 0.045
    assert challenge["currency"] == "USDC"
    assert challenge["route"] == "/api/v1/niche-test/item_abc123/process"
    
    # 4. Verification of parameterized matching for preconfigured route
    # Route: /api/v1/pgl/{agent_id}/quarantine -> Price: 0.01 USDC
    quarantine_resp = client.post("/api/v1/pgl/agent_xyz_99/quarantine", json={})
    assert quarantine_resp.status_code == 402
    quarantine_challenge = quarantine_resp.json()
    assert quarantine_challenge["error"] == "payment_required"
    assert quarantine_challenge["amount"] == 0.01
    assert quarantine_challenge["currency"] == "USDC"
    assert quarantine_challenge["route"] == "/api/v1/pgl/agent_xyz_99/quarantine"

