"""
Banker Agent Router — Operator-triggered payment ledger endpoints.

Gold-Standard Architecture:
  The backend is NOT the signer. The operator's Base Account wallet (connected
  via @base-org/account in the control plane) is the signer.

Routes:
  POST /api/v1/banker/pay/prepare  — Create idempotency-checked pending row
  POST /api/v1/banker/pay/confirm  — Verify Base receipt and record settlement proof
  GET  /api/v1/banker/ledger       — Paginated payment history
  GET  /api/v1/banker/status       — Wallet config and treasury address
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config.settings import settings
from backend.core.database.database import get_db
from backend.core.services.banker_agent import (
    BankerAgentService,
    BankerAgentError,
    BankerAgentConfigError,
    BankerAgentDuplicatePaymentError,
    BankerAgentProofError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/banker", tags=["Banker Agent"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class BankerStatusResponse(BaseModel):
    treasury_address:   Optional[str]
    configured:         bool
    usdc_contract:      str
    network:            str
    chain_id:           int


class PreparePaymentRequest(BaseModel):
    payment_object_type: str  = Field(..., description="Identifier type for idempotency (e.g. 'invoice', 'settlement')")
    payment_object_id:   int  = Field(..., description="Identifier ID for idempotency")
    to_address:          str  = Field(..., description="Recipient EVM address (0x...)")
    amount:              float = Field(..., gt=0, description="Amount to send")
    asset:               str  = Field("USDC", description="Asset ticker (e.g. USDC)")


class ConfirmPaymentRequest(BaseModel):
    payment_object_type: str       = Field(..., description="Must match the prepare request")
    payment_object_id:   int       = Field(..., description="Must match the prepare request")
    tx_hash:             str       = Field(..., description="Transaction hash from Base Account wallet provider")
    chain_id:            int       = Field(8453, description="Chain ID (default: Base Mainnet 8453)")
    block_number:        Optional[int]  = Field(None, description="Block number from receipt")
    gas_used:            Optional[int]  = Field(None, description="Gas used from receipt")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/status", response_model=BankerStatusResponse)
async def banker_status():
    """
    Returns Banker Agent configuration.
    The treasury address is the Base Account that receives incoming x402 payments
    and from which operator-triggered outgoing payments are sent.
    """
    treasury_address = None
    configured = False
    try:
        treasury_address = BankerAgentService.get_treasury_address()
        configured = True
    except BankerAgentConfigError:
        pass

    return BankerStatusResponse(
        treasury_address = treasury_address,
        configured       = configured,
        usdc_contract    = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",  # Base Mainnet USDC
        network          = "base",
        chain_id         = 8453,
    )


@router.post("/pay/prepare")
async def banker_prepare_payment(
    body: PreparePaymentRequest,
    db:   AsyncSession = Depends(get_db),
):
    """
    Step 1 of 2 in the payment flow.

    Validates idempotency and creates a pending Payment row in the database.
    Returns the payment record so the frontend can proceed to call the
    Base Account wallet provider (wallet_sendCalls / eth_sendTransaction).
    """
    try:
        payment = await BankerAgentService.prepare_payment(
            db=db,
            payment_object_type=body.payment_object_type,
            payment_object_id=body.payment_object_id,
            to_address=body.to_address,
            amount=body.amount,
            asset=body.asset,
        )
    except BankerAgentDuplicatePaymentError as exc:
        raise HTTPException(status_code=409, detail=f"Duplicate payment: {exc}")
    except BankerAgentConfigError as exc:
        raise HTTPException(status_code=503, detail=f"Banker not configured: {exc}")
    except BankerAgentError as exc:
        raise HTTPException(status_code=500, detail=f"Payment preparation failed: {exc}")

    return payment


@router.post("/pay/confirm")
async def banker_confirm_payment(
    body: ConfirmPaymentRequest,
    db:   AsyncSession = Depends(get_db),
):
    """
    Step 2 of 2 in the payment flow.

    Called by the frontend after the Base Account wallet provider returns
    the transaction hash. The backend verifies the Base USDC receipt before
    recording settlement proof on the pending row.
    """
    try:
        payment = await BankerAgentService.confirm_payment(
            db=db,
            payment_object_type=body.payment_object_type,
            payment_object_id=body.payment_object_id,
            tx_hash=body.tx_hash,
            chain_id=body.chain_id,
            block_number=body.block_number,
            gas_used=body.gas_used,
        )
    except BankerAgentDuplicatePaymentError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except BankerAgentProofError as exc:
        raise HTTPException(status_code=409, detail=f"Payment proof rejected: {exc}")
    except BankerAgentError as exc:
        raise HTTPException(status_code=500, detail=f"Payment confirmation failed: {exc}")

    return payment


@router.get("/ledger")
async def banker_ledger(
    page:     int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns paginated payment history from the payments table, newest-first.
    """
    return await BankerAgentService.get_ledger(
        db=db,
        page=page,
        per_page=per_page,
        status_filter=status_filter,
    )
