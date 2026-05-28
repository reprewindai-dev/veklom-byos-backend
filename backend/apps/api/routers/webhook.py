"""Webhook handler for payment confirmations with HMAC verification."""

import hashlib
import hmac
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Header
from pydantic import BaseModel

from backend.core.config.settings import settings
from backend.core.database.database import get_db
from backend.core.security.auth import get_current_user
from backend.db.models.billing import Order, Ledger
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


class WebhookResponse(BaseModel):
    ok: bool
    message: str


# ---------------------------------------------------------------------------
# In-memory replay cache (for idempotency)
# ---------------------------------------------------------------------------
# In production, use Redis or a database table for this
_webhook_cache: dict = {}


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


def is_replay(payload_hash: str) -> bool:
    """Check if this webhook payload has already been processed."""
    return payload_hash in _webhook_cache


def mark_processed(payload_hash: str):
    """Mark a webhook payload as processed."""
    _webhook_cache[payload_hash] = datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Webhook endpoint
# ---------------------------------------------------------------------------

@router.post("/payment")
async def payment_webhook(
    payload: WebhookPayload,
    request: Request,
    x_signature: Optional[str] = Header(None, alias="X-Signature"),
    db: AsyncSession = Depends(get_db)
):
    """
    Handle payment confirmation webhook from relayer.
    
    Verifies HMAC signature, ensures idempotency, and updates ledger.
    """
    from sqlalchemy import select
    
    # Read raw body for signature verification
    raw_body = await request.body()
    payload_hash = hashlib.sha256(raw_body).hexdigest()
    
    # Check replay cache
    if is_replay(payload_hash):
        return WebhookResponse(ok=True, message="Already processed (idempotent)")
    
    # Verify HMAC signature
    if not settings.WEBHOOK_SECRET:
        # In development, skip verification if no secret is set
        pass
    elif not x_signature or not verify_webhook_signature(raw_body, x_signature, settings.WEBHOOK_SECRET):
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    # Process the webhook
    if payload.type == "tx_confirmed":
        # Find the order
        result = await db.execute(
            select(Order).where(Order.order_id == payload.order_id)
        )
        order = result.scalar_one_or_none()
        
        if not order:
            # Order not found - this is okay for idempotency
            mark_processed(payload_hash)
            return WebhookResponse(ok=True, message="Order not found (idempotent)")
        
        # Update order status
        if order.status != "confirmed":
            order.status = "confirmed"
            order.tx_hash = payload.tx_hash
            order.updated_at = datetime.now(timezone.utc)
            
            # Create ledger entry
            ledger_entry = Ledger(
                order_id=payload.order_id,
                entry_type="payment",
                amount=order.amount,
                tx_hash=payload.tx_hash,
                meta={
                    "confirmations": payload.confirmations,
                    "webhook_type": payload.type
                }
            )
            db.add(ledger_entry)
            
            await db.commit()
    
    # Mark as processed
    mark_processed(payload_hash)
    
    return WebhookResponse(ok=True, message="Webhook processed successfully")


@router.get("/health")
async def webhook_health():
    """Health check for webhook endpoint."""
    return {
        "status": "healthy",
        "cache_size": len(_webhook_cache),
        "webhook_secret_configured": bool(settings.WEBHOOK_SECRET)
    }
