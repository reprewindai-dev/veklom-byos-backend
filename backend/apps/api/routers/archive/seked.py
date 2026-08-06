from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from backend.core.database.database import get_db
import time
import random
import hashlib
import uuid

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
        from backend.db.models.pgl import PGLIdentity
        from backend.db.models.evidence import EvidencePack, BrowserAction
        from backend.db.models.security import AuditLog
        from sqlalchemy import select, func
        from datetime import datetime, timedelta, timezone
        
        # Get active identities
        result = await db.execute(select(PGLIdentity).limit(50))
        identities = result.scalars().all()
        
        # Time window for metrics
        recent_window = datetime.now(timezone.utc) - timedelta(hours=1)
        
        seked_agents = []
        for ident in identities:
            # Calculate real metrics using Evidence Packs and Actions
            # E (Energy): Volume of recent actions
            action_count = await db.scalar(
                select(func.count(BrowserAction.id))
                .where(BrowserAction.agent_id == ident.id)
                .where(BrowserAction.started_at >= recent_window)
            ) or 0
            
            # R (Resistance): Recent errors or failed actions
            error_count = await db.scalar(
                select(func.count(BrowserAction.id))
                .where(BrowserAction.agent_id == ident.id)
                .where(BrowserAction.success == False)
                .where(BrowserAction.started_at >= recent_window)
            ) or 0
            
            # Audit anomalies
            audit_errors = await db.scalar(
                select(func.count(AuditLog.id))
                .where(AuditLog.user_id == ident.id)
                .where(AuditLog.action.like("%fail%"))
                .where(AuditLog.created_at >= recent_window)
            ) or 0
            
            # C (Capacity): Historical evidence packs (experience)
            evidence_count = await db.scalar(
                select(func.count(EvidencePack.id))
                .where(EvidencePack.agent_id == ident.id)
            ) or 0
            
            # S (Stability): Ratio of successful to failed operations globally
            total_actions = await db.scalar(select(func.count(BrowserAction.id)).where(BrowserAction.agent_id == ident.id)) or 1
            total_success = await db.scalar(select(func.count(BrowserAction.id)).where(BrowserAction.agent_id == ident.id, BrowserAction.success == True)) or 0
            
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
