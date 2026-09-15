import hashlib
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database.database import get_db

router = APIRouter(prefix="/seked", tags=["SEKED Monitoring"])

class SekedMeasurement(BaseModel):
    E: int
    R: int
    C: int
    D: int
    S: int
    timestamp: str

@router.post("/calculate")
async def calculate_ratios(measurement: SekedMeasurement):
    sigma = round((measurement.E + measurement.D) / (measurement.R + 1), 2)
    ci = round(measurement.C / max(10 - measurement.R, 1), 2)
    si = round(measurement.S / 10.0, 2)
    return {
        "sigma": sigma,
        "ci": ci,
        "si": si
    }

@router.get("/directive/{ratio}")
async def get_directive(ratio: float):
    if ratio >= 7.0:
        return {
            "ratio": ratio,
            "directive": "Execute payment processing with enhanced monitoring",
            "action_type": "EXECUTE",
            "confidence": 0.92,
            "reasoning": "High energy and drive with low resistance indicates optimal execution state"
        }
    elif ratio >= 4.0:
        return {
            "ratio": ratio,
            "directive": "Prepare for execution, monitor metrics closely",
            "action_type": "PREPARE",
            "confidence": 0.85,
            "reasoning": "Moderate energy and drive indicates readiness but not optimal state"
        }
    elif ratio >= 2.0:
        return {
            "ratio": ratio,
            "directive": "Conserve resources, delay execution",
            "action_type": "CONSERVE",
            "confidence": 0.75,
            "reasoning": "Low energy and high resistance indicates need to conserve resources"
        }
    else:
        return {
            "ratio": ratio,
            "directive": "Implement recovery protocols immediately",
            "action_type": "RECOVER",
            "confidence": 0.95,
            "reasoning": "Critical state, immediate recovery required"
        }

@router.post("/state")
async def create_state(measurement: SekedMeasurement):
    state_id = f"seked_st_{uuid.uuid4().hex[:8]}"
    fingerprint = hashlib.sha256(f"{measurement.E}{measurement.R}{measurement.C}{measurement.D}{measurement.S}{measurement.timestamp}".encode()).hexdigest()
    return {
        "id": state_id,
        "measurement": measurement.dict(),
        "fingerprint": fingerprint,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status": "active"
    }

@router.get("/agents")
async def get_seked_agents(db: AsyncSession = Depends(get_db)):
    """
    Returns SEKED metric data for agents in the workspace.
    Queries the AgentIdentity and AuditLog to calculate execution confidence metrics.
    """
    try:
        from datetime import datetime, timedelta, timezone

        from sqlalchemy import case, func, select

        from backend.db.models.evidence import BrowserAction, EvidencePack
        from backend.db.models.pgl import PGLIdentity
        from backend.db.models.security import AuditLog

        # Get active identities
        result = await db.execute(select(PGLIdentity).limit(50))
        identities = result.scalars().all()

        # Time window for metrics
        recent_window = datetime.now(timezone.utc) - timedelta(hours=1)

        ident_ids = [ident.id for ident in identities]

        # Pre-fetch BrowserAction metrics
        browser_action_metrics = {}
        if ident_ids:
            ba_stmt = select(
                BrowserAction.agent_id,
                func.sum(case((BrowserAction.started_at >= recent_window, 1), else_=0)).label("recent_count"),
                func.sum(case((BrowserAction.success == False, case((BrowserAction.started_at >= recent_window, 1), else_=0)), else_=0)).label("recent_error_count"),
                func.count(BrowserAction.id).label("total_actions"),
                func.sum(case((BrowserAction.success == True, 1), else_=0)).label("total_success")
            ).where(BrowserAction.agent_id.in_(ident_ids)).group_by(BrowserAction.agent_id)

            ba_result = await db.execute(ba_stmt)
            for row in ba_result.all():
                browser_action_metrics[row.agent_id] = {
                    "action_count": row.recent_count or 0,
                    "error_count": row.recent_error_count or 0,
                    "total_actions": row.total_actions or 1,
                    "total_success": row.total_success or 0
                }

        # Pre-fetch AuditLog metrics
        audit_metrics = {}
        if ident_ids:
            audit_stmt = select(
                AuditLog.user_id,
                func.sum(case((AuditLog.action.like("%fail%"), case((AuditLog.created_at >= recent_window, 1), else_=0)), else_=0)).label("audit_errors")
            ).where(AuditLog.user_id.in_(ident_ids)).group_by(AuditLog.user_id)

            audit_result = await db.execute(audit_stmt)
            for row in audit_result.all():
                audit_metrics[row.user_id] = row.audit_errors or 0

        # Pre-fetch EvidencePack metrics
        evidence_metrics = {}
        if ident_ids:
            ev_stmt = select(
                EvidencePack.agent_id,
                func.count(EvidencePack.id).label("evidence_count")
            ).where(EvidencePack.agent_id.in_(ident_ids)).group_by(EvidencePack.agent_id)

            ev_result = await db.execute(ev_stmt)
            for row in ev_result.all():
                evidence_metrics[row.agent_id] = row.evidence_count or 0

        seked_agents = []
        for ident in identities:
            ba_data = browser_action_metrics.get(ident.id, {"action_count": 0, "error_count": 0, "total_actions": 1, "total_success": 0})
            action_count = ba_data["action_count"]
            error_count = ba_data["error_count"]
            total_actions = ba_data["total_actions"]
            total_success = ba_data["total_success"]

            audit_errors = audit_metrics.get(ident.id, 0)
            evidence_count = evidence_metrics.get(ident.id, 0)

            E = min(max(int(action_count / 10), 1), 10)
            R = min(max(int((error_count + audit_errors) / 2), 1), 10)
            C = min(max(int(evidence_count / 5), 1), 10)
            D = max(E - R, 1) # Drive correlates with successful energy
            S = min(max(int((total_success / max(total_actions, 1)) * 10), 1), 10)

            sigma = round((E + D) / (R + 1), 2)
            ci = round(C / max(10 - R, 1), 2)
            si = round(S / 10.0, 2)

            # Decide directive
            directive_info = await get_directive(sigma)

            seked_agents.append({
                "agent_id": ident.id,
                "name": ident.id[:8], # Fallback since PGLIdentity has no name currently
                "status": ident.metadata_json.get("status", "active") if getattr(ident, "metadata_json", None) else "active",
                "measurement": { "E": E, "R": R, "C": C, "D": D, "S": S, "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()) },
                "ratios": { "sigma": sigma, "ci": ci, "si": si },
                "directive": directive_info,
                "last_updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "performance_metrics": {
                    "response_time_ms": 250, # Should calculate avg execution_time_ms
                    "success_rate": round(total_success / max(total_actions, 1), 3),
                    "error_rate": round(1.0 - (total_success / max(total_actions, 1)), 3),
                    "throughput": action_count
                }
            })

        return seked_agents
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch SEKED agents from database: {str(e)}"
        )
