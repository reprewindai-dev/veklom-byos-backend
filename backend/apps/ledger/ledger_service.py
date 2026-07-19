import hashlib
import uuid
import logging
from typing import Dict, List
from datetime import datetime, timezone
from fastapi.responses import JSONResponse

from backend.apps.ledger.schemas import PaymentRequest, PaymentReceiptResponse, LedgerProofResponse

logger = logging.getLogger(__name__)

# Mocked state for in-memory ledger representation
_mock_ledger_receipts: Dict[str, dict] = {}

class LedgerService:
    @staticmethod
    async def issue_receipt(request: PaymentRequest) -> PaymentReceiptResponse:
        """Issue a cryptographic receipt for a paid compute task."""
        
        # Simulate payment validation here (e.g. hitting Stripe or a web3 wallet)
        # If insufficient funds: 
        # return LedgerService._build_402_response("insufficient_funds")
        
        receipt_id = f"x402_{uuid.uuid4().hex[:16]}"
        now = datetime.now(timezone.utc)
        
        # Cryptographically tie the execution to the payment
        evidence_payload = f"{receipt_id}:{request.tenant_id}:{request.capability_id}:{request.execution_hash}:{now.isoformat()}"
        evidence_hash = hashlib.sha256(evidence_payload.encode()).hexdigest()
        
        receipt_record = {
            "receipt_id": receipt_id,
            "tenant_id": request.tenant_id,
            "amount": request.amount,
            "evidence_hash": evidence_hash,
            "status": "SETTLED",
            "timestamp": now.isoformat()
        }
        
        logger.info(f"[LEDGER_LOG] Issued x402 receipt {receipt_id} for tenant {request.tenant_id}")
        _mock_ledger_receipts[receipt_id] = receipt_record
        
        return PaymentReceiptResponse(
            receipt_id=receipt_id,
            tenant_id=request.tenant_id,
            amount=request.amount,
            evidence_hash=evidence_hash,
            status="SETTLED",
            timestamp=now
        )

    @staticmethod
    async def verify_receipt(receipt_id: str) -> LedgerProofResponse:
        """Verify an existing receipt using a mocked Merkle proof structure."""
        if receipt_id not in _mock_ledger_receipts:
            raise ValueError("Receipt not found")
            
        # Generate dummy proof based on the receipt's evidence hash
        receipt = _mock_ledger_receipts[receipt_id]
        merkle_root = hashlib.sha256(b"mock_ledger_root").hexdigest()
        dummy_proof = [hashlib.sha256(receipt["evidence_hash"].encode()).hexdigest()]
        
        return LedgerProofResponse(
            receipt_id=receipt_id,
            merkle_root=merkle_root,
            inclusion_proof=dummy_proof,
            is_valid=True
        )

    @staticmethod
    def _build_402_response(reason: str) -> JSONResponse:
        """Builds a standardized 402 Payment Required response as mandated by AGENTS.md."""
        return JSONResponse(
            status_code=402,
            content={
                "error": "Payment Required",
                "code": "x402_insufficient_funds",
                "reason": reason,
                "message": "Insufficient funds or missing settlement proof to execute this capability."
            },
            headers={"X-Veklom-Error": "402"}
        )

    @staticmethod
    def get_recent_receipts() -> List[dict]:
        """Used by Source of Truth snapshot to aggregate receipts."""
        return list(_mock_ledger_receipts.values())[-10:]
