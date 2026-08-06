from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import JSONResponse
import json
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from backend.core.database.database import get_db
from backend.core.security.auth import get_current_user_optional
from backend.db.models.security import AuditLog
from backend.db.models.ai import IncidentLog
from backend.db.models.ledger import SettlementLedger

router = APIRouter(prefix="", tags=["Diagnostics"])

@router.get("/api/health")
async def diagnostics_health(db: AsyncSession = Depends(get_db)):
    # Verify DB connectivity
    await db.execute(select(func.count()).select_from(AuditLog))
    return {"status": "ok", "message": "Enterprise Diagnostics Engine Operational"}

@router.post("/api/mock-webhook")
async def mock_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        payload = await request.json()
    except Exception:
        payload = {"raw_body": (await request.body()).decode("utf-8")}
        
    log = AuditLog(
        workspace_id="global",
        action="diagnostics.webhook.received",
        resource_type="webhook_payload",
        resource_id="webhook_" + datetime.utcnow().strftime("%Y%m%d%H%M%S"),
        details=payload
    )
    db.add(log)
    await db.commit()
    return {"status": "recorded", "id": log.id}

@router.get("/api/webhook-logs")
async def get_webhook_logs(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.action == "diagnostics.webhook.received")
        .order_by(AuditLog.created_at.desc())
        .limit(50)
    )
    logs = result.scalars().all()
    return [{"id": l.id, "created_at": l.created_at, "payload": l.details} for l in logs]

@router.post("/api/trigger-alert")
async def trigger_alert(body: dict, db: AsyncSession = Depends(get_db)):
    severity = body.get("severity", "WARNING")
    message = body.get("message", "Test Alert Triggered")
    
    incident = IncidentLog(
        workspace_id=body.get("workspace_id", "global"),
        severity=severity,
        message=message,
        resolved=False
    )
    db.add(incident)
    
    # Also log it
    log = AuditLog(
        workspace_id=incident.workspace_id,
        action="diagnostics.alert.triggered",
        resource_type="incident_log",
        resource_id=incident.id,
        details={"severity": severity, "message": message}
    )
    db.add(log)
    await db.commit()
    return {"status": "alert_created", "incident_id": incident.id}

@router.post("/api/analyze-ledger")
async def analyze_ledger(body: dict, db: AsyncSession = Depends(get_db)):
    # Perform actual ledger analysis
    total_txs = await db.scalar(select(func.count(SettlementLedger.id))) or 0
    total_volume = await db.scalar(select(func.sum(SettlementLedger.amount))) or 0
    
    return {
        "status": "analysis_complete",
        "metrics": {
            "total_transactions": total_txs,
            "total_volume_minor": total_volume,
            "average_transaction": round(total_volume / max(total_txs, 1), 2)
        }
    }
