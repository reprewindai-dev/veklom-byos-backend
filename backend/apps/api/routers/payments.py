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
import httpx
import logging
from backend.core.config.settings import settings

logger = logging.getLogger(__name__)



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
    
    This implementation uses standard HTTP JSON-RPC to avoid heavy Web3 library dependencies,
    aligning with the codebase's existing pattern in x402 middleware.
    """
    from sqlalchemy import select
    
    try:
        rpc_endpoints = [settings.FLASHBLOCKS_RPC_URL] if getattr(settings, "FLASHBLOCKS_RPC_URL", "") else []
        rpc_endpoints.extend([
            "https://mainnet.base.org",
            "https://base.llamarpc.com",
            "https://base-rpc.publicnode.com"
        ])

        tx_receipt = None
        tx_data = None
        max_retries = 30
        poll_interval = 2
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            for _ in range(max_retries):
                for rpc_url in rpc_endpoints:
                    try:
                        # 1. Fetch transaction receipt to check confirmation status
                        receipt_payload = {
                            "jsonrpc": "2.0",
                            "method": "eth_getTransactionReceipt",
                            "params": [tx_hash],
                            "id": 1
                        }
                        res = await client.post(rpc_url, json=receipt_payload)
                        if res.status_code == 200:
                            data = res.json()
                            if "result" in data and data["result"] is not None:
                                tx_receipt = data["result"]

                        # 2. Fetch transaction data to verify recipient, token, amount
                        tx_payload = {
                            "jsonrpc": "2.0",
                            "method": "eth_getTransactionByHash",
                            "params": [tx_hash],
                            "id": 2
                        }
                        res_tx = await client.post(rpc_url, json=tx_payload)
                        if res_tx.status_code == 200:
                            data_tx = res_tx.json()
                            if "result" in data_tx and data_tx["result"] is not None:
                                tx_data = data_tx["result"]

                        if tx_receipt and tx_data:
                            break
                    except Exception as e:
                        logger.warning(f"RPC check failed on {rpc_url}: {e}")
                        continue

                if tx_receipt and tx_data:
                    break

                await asyncio.sleep(poll_interval)
        
        # Verify receipt.status == 1 (0x1)
        if tx_receipt and tx_receipt.get("status") == "0x1" and tx_data:
            # Get the payment record
            result = await db.execute(
                select(Payment).where(Payment.order_id == order_id)
            )
            payment = result.scalar_one_or_none()
            
            if payment:
                # Security Verification
                treasury = getattr(settings, "VEKLOM_TREASURY_ADDRESS", "").lower()
                to_address = (tx_data.get("to") or "").lower()

                is_valid = False
                expected_token = payment.token_contract.lower() if payment.token_contract else None

                if expected_token and expected_token != "native":
                    # Simple ERC20 check
                    if to_address == expected_token:
                        input_data = tx_data.get("input", "")
                        # 0xa9059cbb is transfer(address,uint256)
                        if input_data.startswith("0xa9059cbb") and len(input_data) >= 138:
                            recipient_in_data = "0x" + input_data[34:74]
                            amount_in_data_hex = input_data[74:138]
                            try:
                                actual_amount = int(amount_in_data_hex, 16)
                                expected_amount_wei = int(payment.expected_amount * (10 ** 6)) # assuming USDC/USDT 6 decimals
                                if recipient_in_data == treasury and actual_amount >= expected_amount_wei:
                                    is_valid = True
                            except ValueError:
                                pass
                else:
                    # Native transfer
                    if to_address == treasury:
                        # Verify amount (value is in wei)
                        val = int(tx_data.get("value", "0x0"), 16)
                        expected_amount_wei = int(payment.expected_amount * (10 ** 18))
                        if val >= expected_amount_wei:
                            is_valid = True

                if is_valid:
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
                else:
                    payment.status = "failed"
                    await db.commit()
                    logger.warning(f"Payment {order_id} failed security verification (amount/token/recipient mismatch).")
        else:
            # Mark as failed if no receipt or failed status
            result = await db.execute(
                select(Payment).where(Payment.order_id == order_id)
            )
            payment = result.scalar_one_or_none()
            if payment:
                payment.status = "failed"
                await db.commit()
            
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
