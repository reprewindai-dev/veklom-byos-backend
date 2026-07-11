import os
os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres:postgres@localhost:5432/veklom"
os.environ["POSTGRES_DB"] = "veklom"

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
from contextlib import asynccontextmanager

from backend.core.middleware.x402 import X402PaymentMiddleware
from backend.core.config.settings import settings
import uuid

app = FastAPI()
app.add_middleware(X402PaymentMiddleware)

@app.post("/api/v1/ai/inference")
async def dummy_inference(request: Request):
    if getattr(request.state, "x402_paid", False) is False:
        pass
    return JSONResponse({"status": "success", "message": "inference done"})

@app.post("/api/v1/ai/fail")
async def dummy_fail(request: Request):
    return JSONResponse(status_code=500, content={"error": "simulated failure"})

client = TestClient(app)

# Helper to mock db session correctly
def mock_db_session_cm(mock_db):
    @asynccontextmanager
    async def _mock_db_session():
        yield mock_db
    return _mock_db_session

@patch("backend.core.middleware.x402._today_key", return_value="test_ip")
@patch("backend.core.middleware.x402._free_usage", {"test_ip": 5})
def test_x402_middleware_no_auth(mock_today):
    # Calling a paid endpoint without auth should return 402 if free quota exhausted
    response = client.post("/api/v1/ai/inference")
    assert response.status_code == 402
    assert response.json()["error"] == "payment_required"

@patch("backend.core.middleware.x402._today_key", return_value="test_ip")
@patch("backend.core.middleware.x402._free_usage", {"test_ip": 5})
@patch("backend.core.middleware.x402._verify_workspace_auth", new_callable=AsyncMock)
@patch("backend.core.database.database.get_db_session")
def test_x402_middleware_sufficient_balance(mock_get_db_session, mock_verify_auth, mock_today):
    mock_verify_auth.return_value = {"sub": "user-123"}
    
    mock_db = AsyncMock()
    mock_get_db_session.side_effect = mock_db_session_cm(mock_db)
    
    mock_db.execute.return_value = MagicMock(
        scalar_one_or_none=MagicMock(side_effect=[
            MagicMock(workspace_id="ws-123"),
            None,
            MagicMock(license_tier="growth")
        ]),
        scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
    )
    
    mock_db.scalar.side_effect = [0.10, 0.00]
    
    with patch("backend.core.middleware.x402.create_and_persist_receipt", new_callable=AsyncMock) as mock_receipt:
        mock_receipt.return_value = {
            "receipt_id": "rcpt_123",
            "request_id": "req_123",
            "evidence_hash": "ev_123",
            "amount": 0.008,
            "policy_decision": "passed"
        }
        
        response = client.post("/api/v1/ai/inference", headers={"Authorization": "Bearer fake_token"})
        
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        
        assert "X-Veklom-Receipt-ID" in response.headers
        assert response.headers["X-Veklom-Receipt-ID"] == "rcpt_123"

@patch("backend.core.middleware.x402._today_key", return_value="test_ip")
@patch("backend.core.middleware.x402._free_usage", {"test_ip": 5})
@patch("backend.core.middleware.x402._verify_workspace_auth", new_callable=AsyncMock)
@patch("backend.core.database.database.get_db_session")
def test_x402_middleware_insufficient_balance(mock_get_db_session, mock_verify_auth, mock_today):
    mock_verify_auth.return_value = {"sub": "user-123"}
    
    mock_db = AsyncMock()
    mock_get_db_session.side_effect = mock_db_session_cm(mock_db)
    
    mock_db.execute.return_value = MagicMock(
        scalar_one_or_none=MagicMock(side_effect=[
            MagicMock(workspace_id="ws-123"),
            None,
            MagicMock(license_tier="growth")
        ]),
        scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
    )
    
    mock_db.scalar.side_effect = [0.005, 0.00]
    
    response = client.post("/api/v1/ai/inference", headers={"Authorization": "Bearer fake_token"})
    
    assert response.status_code == 402
    assert "Insufficient funds" in response.json()["detail"]

@patch.dict("backend.core.middleware.x402._PAID_ROUTES", {"POST:/api/v1/ai/fail": {"price_usdc": 0.008, "name": "Fail Test", "free_daily": 0}})
@patch("backend.core.middleware.x402._today_key", return_value="test_ip")
@patch("backend.core.middleware.x402._free_usage", {"test_ip": 5})
@patch("backend.core.middleware.x402._verify_workspace_auth", new_callable=AsyncMock)
@patch("backend.core.database.database.get_db_session")
def test_x402_middleware_execution_failure_refunds(mock_get_db_session, mock_verify_auth, mock_today):
    mock_verify_auth.return_value = {"sub": "user-123"}
    
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_get_db_session.side_effect = mock_db_session_cm(mock_db)
    
    mock_db.execute.return_value = MagicMock(
        scalar_one_or_none=MagicMock(side_effect=[
            MagicMock(workspace_id="ws-123"),
            None,
            MagicMock(license_tier="growth")
        ]),
        scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
    )
    
    mock_db.scalar.side_effect = [0.10, 0.00]
    
    with patch("backend.core.middleware.x402.create_and_persist_receipt", new_callable=AsyncMock) as mock_receipt:
        mock_receipt.return_value = {
            "receipt_id": "rcpt_fail",
            "request_id": "req_fail",
            "evidence_hash": "ev_fail",
            "amount": 0.008,
            "policy_decision": "passed"
        }
        
        response = client.post("/api/v1/ai/fail", headers={"Authorization": "Bearer fake_token"})
        
        assert response.status_code == 500
        
        add_calls = mock_db.add.call_args_list
        assert len(add_calls) >= 2
        
        refund_txn = add_calls[1][0][0]
        assert refund_txn.__class__.__name__ == "WalletTransaction"
        assert refund_txn.tx_type == "credit"
        assert "Refunded" in refund_txn.description
