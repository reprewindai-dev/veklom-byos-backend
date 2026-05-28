"""Admin API endpoints for billing reconciliation and webhook monitoring."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, Optional
from datetime import datetime, timezone

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
    
    # TODO: Trigger actual webhook retry logic here
    
    return {"status": "retrying", "entry_id": entry_id, "retry_count": entry.retry_count}


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
    # Count total findings
    findings_query = select(ReconFinding)
    findings_result = await db.execute(findings_query)
    total_findings = len(findings_result.scalars().all())
    
    # Count dead-letter entries by status
    dead_letter_query = select(WebhookDeadLetter)
    dead_letter_result = await db.execute(dead_letter_query)
    dead_letters = dead_letter_result.scalars().all()
    
    status_counts = {}
    for dl in dead_letters:
        status_counts[dl.status] = status_counts.get(dl.status, 0) + 1
    
    return {
        "recon_findings": {
            "total": total_findings,
            "recent_count": total_findings  # Could add time-based filtering
        },
        "webhook_dead_letter": {
            "total": len(dead_letters),
            "by_status": status_counts
        }
    }
