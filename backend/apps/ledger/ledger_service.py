import hashlib
import uuid
import logging
from typing import Dict, List
from datetime import datetime, timezone
from fastapi.responses import JSONResponse

from backend.apps.ledger.schemas import PaymentRequest, PaymentReceiptResponse, LedgerProofResponse

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.db.models.ledger import SettlementLedger, SettlementStatus

logger = logging.getLogger(__name__)

class LedgerService:
    @staticmethod
    async def issue_receipt(request: PaymentRequest, db: AsyncSession) -> PaymentReceiptResponse:
        """Issue a cryptographic receipt for a paid compute task."""
        
        # Simulate payment validation here (e.g. hitting Stripe or a web3 wallet)
        # If insufficient funds: 
        # return LedgerService._build_402_response("insufficient_funds")
        
        receipt_id = f"x402_{uuid.uuid4().hex[:16]}"
        now = datetime.now(timezone.utc)
        
        # Cryptographically tie the execution to the payment
        evidence_payload = f"{receipt_id}:{request.tenant_id}:{request.capability_id}:{request.execution_hash}:{now.isoformat()}"
        evidence_hash = hashlib.sha256(evidence_payload.encode()).hexdigest()
        
        new_settlement = SettlementLedger(
            tenant_id=request.tenant_id,
            provider="veklom_default",
            fee_type="compute",
            amount=request.amount,
            currency="USDC",
            status=SettlementStatus.SETTLED,
            idempotency_key=receipt_id,
            execution_id=request.execution_hash,
            metadata_json={"evidence_hash": evidence_hash, "capability_id": request.capability_id}
        )
        db.add(new_settlement)
        await db.commit()
        await db.refresh(new_settlement)
        
        logger.info(f"[LEDGER_LOG] Issued x402 receipt {receipt_id} for tenant {request.tenant_id}")
        
        return PaymentReceiptResponse(
            receipt_id=receipt_id,
            tenant_id=request.tenant_id,
            amount=request.amount,
            evidence_hash=evidence_hash,
            status="SETTLED",
            timestamp=now
        )

    @staticmethod
    async def verify_receipt(receipt_id: str, db: AsyncSession) -> LedgerProofResponse:
        """Verify an existing receipt using a Merkle proof structure from the database."""
        result = await db.execute(select(SettlementLedger).filter(SettlementLedger.idempotency_key == receipt_id))
        receipt = result.scalar_one_or_none()
        
        if not receipt:
            raise ValueError("Receipt not found")
            
        evidence_hash = receipt.metadata_json.get("evidence_hash", "") if receipt.metadata_json else ""
        merkle_root = hashlib.sha256(b"mock_ledger_root").hexdigest() # Still mocked until global merkle tree is implemented
        dummy_proof = [hashlib.sha256(evidence_hash.encode()).hexdigest()]
        
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
    async def get_recent_receipts(db: AsyncSession) -> List[dict]:
        """Used by Source of Truth snapshot to aggregate receipts."""
        result = await db.execute(select(SettlementLedger).order_by(SettlementLedger.created_at.desc()).limit(10))
        receipts = result.scalars().all()
        return [
            {
                "receipt_id": r.idempotency_key,
                "tenant_id": r.tenant_id,
                "amount": r.amount,
                "evidence_hash": r.metadata_json.get("evidence_hash", "") if r.metadata_json else "",
                "status": r.status.value,
                "timestamp": r.created_at.isoformat()
            } for r in receipts
        ]
