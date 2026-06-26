"""GET /capi/receipt/{id} — retrieve signed receipt."""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from ..core import evidence

router = APIRouter(tags=["receipt"])

@router.get("/receipt/{receipt_id}")
async def get_receipt(receipt_id: str):
    """
    Retrieves a signed execution receipt from the evidence store.
    """
    receipt = await evidence.get_receipt(receipt_id)
    if not receipt:
        raise HTTPException(status_code=404, detail="Receipt not found")

    return receipt
