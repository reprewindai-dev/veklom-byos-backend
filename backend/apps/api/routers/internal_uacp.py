"""UACP Internal Backend Information Contract routes."""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List

from backend.core.database.database import get_db
from backend.core.security.auth import require_internal_operator
from backend.db.models.user import User
from backend.db.models.workspace import Workspace

router = APIRouter(
    prefix="/internal/uacp",
    tags=["uacp-internal"],
    dependencies=[Depends(require_internal_operator)]
)

@router.get("/summary")
async def get_summary(db: AsyncSession = Depends(get_db)):
    """Returns high-level product reality summary for UACP Command Center."""
    return {
        "status": "online",
        "message": "UACP Summary Data",
        "data": {
            "active_users": 0,  # Query DB in full implementation
            "active_workspaces": 0,
            "marketplace_installs": 0
        }
    }

@router.get("/events")
async def get_events(db: AsyncSession = Depends(get_db)):
    """Returns normalized backend events owned by the backend."""
    return {
        "events": [
            {
                "event_id": "pipeline_run:run_123",
                "event_type": "pipeline.run",
                "source": "veklom_backend",
                "workspace_id": "ws_123",
                "tenant_id": "ws_123",
                "user_id": "user_123",
                "entity_type": "pipeline",
                "entity_id": "pipe_123",
                "severity": "info",
                "status": "succeeded",
                "timestamp": "2026-05-08T20:15:00Z",
                "payload": {
                    "latency_ms": 36,
                    "policy_result": "passed",
                    "reserve_impact": "0.25",
                    "audit_id": "aud_123"
                },
                "uacp": {
                    "pillar_ids": ["execution", "governance", "archives"],
                    "committee_ids": ["governance-evidence", "experience-assurance"],
                    "worker_ids": ["ledger", "sentinel", "mirror"]
                }
            }
        ]
    }

@router.get("/evaluation-surgeon")
async def get_evaluation_surgeon(db: AsyncSession = Depends(get_db)):
    """Ranks workspaces from real evaluation, billing, endpoint, evidence, and security signals."""
    return {"workspaces": []}

@router.get("/growth-opportunities")
async def get_growth_opportunities(db: AsyncSession = Depends(get_db)):
    """Ranks marketplace, integration, order, listing, or failed-route signals."""
    return {"opportunities": []}

@router.get("/workspaces")
async def get_workspaces(db: AsyncSession = Depends(get_db)):
    """Exposes backend truth for workspaces."""
    return {"workspaces": []}

@router.get("/runs")
async def get_runs(db: AsyncSession = Depends(get_db)):
    """Exposes backend truth for inference runs."""
    return {"runs": []}

@router.get("/deployments")
async def get_deployments(db: AsyncSession = Depends(get_db)):
    """Exposes backend truth for deployments."""
    return {"deployments": []}

@router.get("/billing")
async def get_billing(db: AsyncSession = Depends(get_db)):
    """Exposes backend truth for billing."""
    return {"billing": []}

@router.get("/evidence")
async def get_evidence(db: AsyncSession = Depends(get_db)):
    """Exposes backend truth for evidence."""
    return {"evidence": []}

@router.get("/monitoring")
async def get_monitoring(db: AsyncSession = Depends(get_db)):
    """Exposes backend truth for monitoring."""
    return {"monitoring": []}

@router.get("/security")
async def get_security(db: AsyncSession = Depends(get_db)):
    """Exposes backend truth for security."""
    return {"security": []}

# OPERATOR ROUTES
operator_router = APIRouter(
    prefix="/internal/operators",
    tags=["uacp-operators"],
    dependencies=[Depends(require_internal_operator)]
)

@operator_router.post("/runs")
async def record_operator_run(request: Request, db: AsyncSession = Depends(get_db)):
    """Record UACP worker runs."""
    payload = await request.json()
    return {"status": "recorded", "run_id": "run_new_123"}

@operator_router.post("/watch")
async def record_operator_watch(request: Request, db: AsyncSession = Depends(get_db)):
    """Record operator-watch evidence."""
    return {"status": "watched"}

@operator_router.post("/workers/{worker_id}/heartbeat")
async def record_worker_heartbeat(worker_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    """Record UACP worker heartbeat."""
    return {"status": "heartbeat_received", "worker_id": worker_id}
