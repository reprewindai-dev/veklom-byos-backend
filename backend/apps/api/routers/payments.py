"""Server-side payment confirmation flow with PostHog analytics."""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.core.database.database import get_db
from backend.core.security.auth import get_current_user
from backend.core.services.posthog_client import posthog_service, hash_id
from backend.db.models.billing import Payment
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/payments", tags=["Payments"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class InitiatePaymentRequest(BaseModel):
    expected_amount: float
    token_contract: str
    chain_id: int


class SubmitPaymentRequest(BaseModel):
    order_id: str
    tx_hash: str


class InitiatePaymentResponse(BaseModel):
    order_id: str
    status: str


class SubmitPaymentResponse(BaseModel):
    ok: bool
    message: str


# ---------------------------------------------------------------------------
# Payment endpoints
# ---------------------------------------------------------------------------

@router.post("/initiate")
async def initiate_payment(
    body: InitiatePaymentRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Initiate a payment and create a pending payment record.
    
    Returns an order_id that the client will use to submit the transaction hash.
    """
    order_id = str(uuid.uuid4())
    user_hash = hash_id(user.email)
    
    payment = Payment(
        order_id=order_id,
        user_hash=user_hash,
        user_id=user.id,
        workspace_id=user.workspace_id or "default",
        expected_amount=body.expected_amount,
        token_contract=body.token_contract,
        chain_id=body.chain_id,
        status="pending"
    )
    
    db.add(payment)
    await db.commit()
    
    # Track payment initiated
    posthog_service.payment_initiated(
        distinct_id=user_hash,
        order_id=order_id,
        amount_cents=int(body.expected_amount * 100),
        currency="USD",
        payment_method=f"chain_{body.chain_id}",
        tx_placeholder="pending"
    )
    
    return InitiatePaymentResponse(order_id=order_id, status="pending")


@router.post("/submit")
async def submit_payment(
    body: SubmitPaymentRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Submit a transaction hash for payment confirmation.
    
    The server will watch the chain for transaction confirmation asynchronously.
    This endpoint returns immediately to avoid blocking the client.
    """
    from sqlalchemy import select
    
    result = await db.execute(
        select(Payment).where(Payment.order_id == body.order_id)
    )
    payment = result.scalar_one_or_none()
    
    if not payment:
        raise HTTPException(status_code=404, detail="Payment order not found")
    
    if payment.status != "pending":
        raise HTTPException(status_code=400, detail=f"Payment already {payment.status}")
    
    # Update with tx_hash (will be confirmed asynchronously)
    payment.tx_hash = body.tx_hash
    await db.commit()
    
    # Start async confirmation watcher
    asyncio.create_task(watch_payment_confirmation(body.order_id, body.tx_hash, db))
    
    return SubmitPaymentResponse(ok=True, message="Transaction submitted for confirmation")


async def watch_payment_confirmation(order_id: str, tx_hash: str, db: AsyncSession):
    """
    Async task to watch for transaction confirmation on-chain.
    
    This is a simplified version - in production you would:
    - Use a proper Web3 provider (Alchemy, QuickNode, etc.)
    - Verify the transaction details (amount, token, recipient)
    - Handle retries and timeouts
    - Use webhooks from the provider instead of polling
    """
    from sqlalchemy import select
    
    try:
        # TODO: Integrate with actual Web3 provider
        # For now, we'll simulate confirmation after a delay
        await asyncio.sleep(5)
        
        # In production, you would do something like:
        # from web3 import Web3
        # w3 = Web3(Web3.HTTPProvider(settings.RPC_URL))
        # receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=600, poll_latency=2)
        # Verify receipt.status == 1
        # Verify token contract, amount, and recipient
        
        # Get the payment record
        result = await db.execute(
            select(Payment).where(Payment.order_id == order_id)
        )
        payment = result.scalar_one_or_none()
        
        if payment:
            # Mark as confirmed
            payment.status = "confirmed"
            payment.confirmations = 2  # Default to 2 confirmations
            payment.confirmed_at = datetime.now(timezone.utc)
            await db.commit()
            
            # Track payment confirmed
            posthog_service.payment_confirmed(
                distinct_id=payment.user_hash,
                order_id=order_id,
                tx_hash=tx_hash,
                confirmations=2,
                status="success"
            )
            
    except Exception as e:
        # Mark as failed on error
        try:
            result = await db.execute(
                select(Payment).where(Payment.order_id == order_id)
            )
            payment = result.scalar_one_or_none()
            if payment:
                payment.status = "failed"
                await db.commit()
        except:
            pass


@router.get("/status/{order_id}")
async def get_payment_status(
    order_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get the current status of a payment."""
    from sqlalchemy import select
    
    result = await db.execute(
        select(Payment).where(Payment.order_id == order_id)
    )
    payment = result.scalar_one_or_none()
    
    if not payment:
        raise HTTPException(status_code=404, detail="Payment order not found")
    
    return {
        "order_id": payment.order_id,
        "status": payment.status,
        "tx_hash": payment.tx_hash,
        "confirmations": payment.confirmations,
        "created_at": payment.created_at.isoformat() if payment.created_at else None,
        "confirmed_at": payment.confirmed_at.isoformat() if payment.confirmed_at else None
    }
