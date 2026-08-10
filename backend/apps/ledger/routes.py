from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from backend.apps.ledger.schemas import PaymentRequest, PaymentReceiptResponse, LedgerProofResponse
from backend.apps.ledger.ledger_service import LedgerService
from backend.core.security.auth import get_current_user
from backend.core.database.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/v1/x402", tags=["Settlement Ledger (x402)"])

@router.post("", response_model=PaymentReceiptResponse)
async def issue_receipt(request: PaymentRequest, background_tasks: BackgroundTasks, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Issue a cryptographic receipt for a paid compute task."""
    # Special behavior: we can simulate a 402 rejection if requested amount is negative for testing
    if request.amount < 0:
        return LedgerService._build_402_response("simulated_insufficient_funds")
        
    return await LedgerService.issue_receipt(request, db)

@router.get("/{receipt_id}/proof", response_model=LedgerProofResponse)
async def verify_receipt(receipt_id: str, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Verify an existing receipt using a mocked Merkle proof structure."""
    try:
        return await LedgerService.verify_receipt(receipt_id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
