"""Webhook handler for payment confirmations with HMAC verification and atomic idempotency."""

import hashlib
import hmac
import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Header
from pydantic import BaseModel

from backend.core.config.settings import settings
from backend.core.database.database import get_db
from backend.core.services.redis_cache import redis_cache
from backend.db.models.billing import Order, Ledger, WebhookReceipt
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/webhook", tags=["Webhook"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class WebhookPayload(BaseModel):
    type: str  # tx_confirmed, tx_failed, etc.
    tx_hash: str
    order_id: str
    confirmations: int
    amount: Optional[float] = None


class WebhookResponse(BaseModel):
    status: str
    idempotent: bool
    message: str


# ---------------------------------------------------------------------------
# Signature verification
# ---------------------------------------------------------------------------

def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """
    Verify HMAC signature for webhook payload.
    
    Expected signature format: sha256=HEX_DIGEST
    """
    if not signature.startswith("sha256="):
        return False
    
    expected_digest = signature[7:]  # Remove "sha256=" prefix
    computed_digest = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(computed_digest, expected_digest)


# ---------------------------------------------------------------------------
# Atomic idempotency with database
# ---------------------------------------------------------------------------

async def process_with_idempotency(
    db: AsyncSession,
    idempotency_key: str,
    body_bytes: bytes,
    handler
) -> WebhookResponse:
    """
    Process webhook with atomic idempotency.
    
    First checks Redis cache for fast replay detection, then uses database
    for atomic reservation and processing.
    """
    from sqlalchemy import select, text
    
    digest = hashlib.sha256(body_bytes).hexdigest()
    
    # Fast path: check Redis cache
    cache_key = f"webhook:idem:{idempotency_key}"
    cached_digest = await redis_cache.get(cache_key)
    
    if cached_digest:
        if cached_digest == digest:
            return WebhookResponse(
                status="ok",
                idempotent=True,
                message="Already processed (idempotent)"
            )
        else:
            raise HTTPException(
                status_code=409,
                detail="Idempotency key re-used with different body"
            )
    
    try:
        # Reserve the idempotency key in database
        receipt = WebhookReceipt(
            idempotency_key=idempotency_key,
            body_sha256=digest
        )
        db.add(receipt)
        await db.flush()
    except Exception:
        # Key already exists - check if body matches
        result = await db.execute(
            select(WebhookReceipt).where(WebhookReceipt.idempotency_key == idempotency_key)
        )
        existing = result.scalar_one_or_none()
        
        if not existing or existing.body_sha256 != digest:
            raise HTTPException(
                status_code=409,
                detail="Idempotency key re-used with different body"
            )
        
        # Cache the result in Redis
        await redis_cache.set(cache_key, digest, ttl=3600)
        
        return WebhookResponse(
            status="ok",
            idempotent=True,
            message="Already processed (idempotent)"
        )
    
    # First time - execute handler within same transaction
    try:
        await handler()
        await db.commit()
        
        # Cache the result in Redis
        await redis_cache.set(cache_key, digest, ttl=3600)
        
        return WebhookResponse(
            status="ok",
            idempotent=False,
            message="Webhook processed successfully"
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


# ---------------------------------------------------------------------------
# Webhook endpoint
# ---------------------------------------------------------------------------

@router.post("/payment")
async def payment_webhook(
    request: Request,
    x_idempotency_key: Optional[str] = Header(None, alias="X-Idempotency-Key"),
    x_signature: Optional[str] = Header(None, alias="X-Signature"),
    db: AsyncSession = Depends(get_db)
):
    """
    Handle payment confirmation webhook from relayer.
    
    Verifies HMAC signature, enforces idempotency with X-Idempotency-Key,
    and updates ledger atomically.
    """
    from sqlalchemy import select
    
    # Read raw body for signature verification
    raw_body = await request.body()
    
    # Verify HMAC signature
    if not settings.WEBHOOK_SECRET:
        # In development, skip verification if no secret is set
        pass
    elif not x_signature or not verify_webhook_signature(raw_body, x_signature, settings.WEBHOOK_SECRET):
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    # Require idempotency key
    if not x_idempotency_key:
        raise HTTPException(status_code=400, detail="Missing X-Idempotency-Key")
    
    # Parse payload
    try:
        payload = json.loads(raw_body.decode())
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    
    # Validate payload shape
    if not all(k in payload for k in ["type", "tx_hash", "order_id"]):
        raise HTTPException(status_code=400, detail="Missing required fields")
    
    # Define the handler that does the actual work
    async def handler():
        if payload["type"] == "tx_confirmed":
            # Find the order
            result = await db.execute(
                select(Order).where(Order.order_id == payload["order_id"])
            )
            order = result.scalar_one_or_none()
            
            if not order:
                # Order not found - this is okay for idempotency
                return
            
            # Update order status
            if order.status != "confirmed":
                order.status = "confirmed"
                order.tx_hash = payload["tx_hash"]
                order.updated_at = datetime.now(timezone.utc)
                
                # Create ledger entry
                ledger_entry = Ledger(
                    tx_hash=payload["tx_hash"],
                    order_id=payload["order_id"],
                    amount=payload.get("amount", order.amount),
                    direction="credit",
                    note="tx_confirmed"
                )
                db.add(ledger_entry)
    
    # Process with idempotency
    return await process_with_idempotency(db, x_idempotency_key, raw_body, handler)


@router.get("/health")
async def webhook_health():
    """Health check for webhook endpoint."""
    return {
        "status": "healthy",
        "webhook_secret_configured": bool(settings.WEBHOOK_SECRET)
    }
