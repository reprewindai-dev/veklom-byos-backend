"""Admin API endpoints for billing reconciliation and webhook monitoring."""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database.database import get_db
from backend.core.security.auth import require_internal_operator
from backend.db.models.billing import ReconFinding, WebhookDeadLetter

router = APIRouter(
    prefix="/admin/billing",
    tags=["admin-billing"],
    dependencies=[Depends(require_internal_operator)]
)


@router.get("/recon-findings")
async def list_recon_findings(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """List reconciliation findings for drift detection."""
    query = select(ReconFinding).order_by(desc(ReconFinding.detected_at)).limit(limit).offset(offset)
    result = await db.execute(query)
    findings = result.scalars().all()

    return {
        "findings": [
            {
                "tx_hash": f.tx_hash,
                "ledger_sum": f.ledger_sum,
                "chain_sum": f.chain_sum,
                "drift": abs(f.ledger_sum - f.chain_sum),
                "detected_at": f.detected_at.isoformat() if f.detected_at else None
            }
            for f in findings
        ],
        "count": len(findings)
    }


@router.get("/webhook-dead-letter")
async def list_webhook_dead_letter(
    status: Optional[str] = Query(None, description="Filter by status: pending, retrying, failed, resolved"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """List failed webhook processing entries from dead-letter queue."""
    query = select(WebhookDeadLetter).order_by(desc(WebhookDeadLetter.created_at))

    if status:
        query = query.where(WebhookDeadLetter.status == status)

    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    entries = result.scalars().all()

    return {
        "entries": [
            {
                "id": e.id,
                "idempotency_key": e.idempotency_key,
                "error_message": e.error_message,
                "retry_count": e.retry_count,
                "status": e.status,
                "created_at": e.created_at.isoformat() if e.created_at else None,
                "updated_at": e.updated_at.isoformat() if e.updated_at else None
            }
            for e in entries
        ],
        "count": len(entries)
    }


@router.post("/webhook-dead-letter/{entry_id}/retry")
async def retry_dead_letter_entry(
    entry_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Retry a failed webhook entry from dead-letter queue."""
    query = select(WebhookDeadLetter).where(WebhookDeadLetter.id == entry_id)
    result = await db.execute(query)
    entry = result.scalar_one_or_none()

    if not entry:
        raise HTTPException(status_code=404, detail="Dead-letter entry not found")

    # Update status to retrying
    entry.status = "retrying"
    entry.retry_count += 1
    entry.updated_at = datetime.now(timezone.utc)

    await db.commit()

    # Trigger actual webhook retry logic
    import json

    from backend.apps.api.routers.webhook import handle_webhook_payload, process_with_idempotency

    try:
        body_bytes = json.dumps(entry.payload).encode()

        async def handler():
            await handle_webhook_payload(db, entry.payload)

        await process_with_idempotency(
            db=db,
            idempotency_key=entry.idempotency_key or f"retry-{entry.id}",
            body_bytes=body_bytes,
            handler=handler,
            is_retry=True
        )

        # After successful processing
        # Re-fetch the entry because the db session might have been rolled back or committed
        query = select(WebhookDeadLetter).where(WebhookDeadLetter.id == entry_id)
        result = await db.execute(query)
        updated_entry = result.scalar_one_or_none()

        if updated_entry:
            updated_entry.status = "resolved"
            updated_entry.updated_at = datetime.now(timezone.utc)
            await db.commit()

        return {"status": "resolved", "entry_id": entry_id, "retry_count": entry.retry_count}

    except Exception as e:
        # If it fails again, we need to re-fetch and update status
        query = select(WebhookDeadLetter).where(WebhookDeadLetter.id == entry_id)
        result = await db.execute(query)
        failed_entry = result.scalar_one_or_none()

        if failed_entry:
            failed_entry.status = "failed"
            failed_entry.error_message = str(e)
            failed_entry.updated_at = datetime.now(timezone.utc)
            await db.commit()

        return {"status": "failed", "entry_id": entry_id, "retry_count": entry.retry_count, "error": str(e)}


@router.delete("/webhook-dead-letter/{entry_id}")
async def delete_dead_letter_entry(
    entry_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Delete a dead-letter entry (use with caution)."""
    query = select(WebhookDeadLetter).where(WebhookDeadLetter.id == entry_id)
    result = await db.execute(query)
    entry = result.scalar_one_or_none()

    if not entry:
        raise HTTPException(status_code=404, detail="Dead-letter entry not found")

    await db.delete(entry)
    await db.commit()

    return {"status": "deleted", "entry_id": entry_id}


@router.get("/recon-summary")
async def get_reconciliation_summary(db: AsyncSession = Depends(get_db)):
    """Get summary statistics for reconciliation findings."""
    # Count total findings using DB aggregation
    findings_query = select(func.count()).select_from(ReconFinding)
    total_findings = await db.scalar(findings_query) or 0

    # Count dead-letter entries by status using DB aggregation
    dead_letter_query = select(WebhookDeadLetter.status, func.count()).group_by(WebhookDeadLetter.status)
    dead_letter_result = await db.execute(dead_letter_query)

    status_counts = {}
    total_dead_letters = 0
    for status, count in dead_letter_result.all():
        status_counts[status] = count
        total_dead_letters += count

    return {
        "recon_findings": {
            "total": total_findings,
            "recent_count": total_findings  # Could add time-based filtering
        },
        "webhook_dead_letter": {
            "total": total_dead_letters,
            "by_status": status_counts
        }
    }
