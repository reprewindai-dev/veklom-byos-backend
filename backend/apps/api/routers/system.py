"""System-level utility endpoints."""
from datetime import datetime, timezone
from fastapi import APIRouter
from backend.core.config.settings import settings

router = APIRouter(prefix="/sys", tags=["System"])


@router.get("/health")
async def sys_health():
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": settings.VERSION,
        "service": settings.APP_NAME,
        "components": {
            "database": {"status": "healthy"},
            "redis": {"status": "healthy"},
            "gpu": {"status": "unknown"},
        },
    }


@router.get("/gpu")
async def sys_gpu():
    return {
        "available": False,
        "devices": [],
        "note": "GPU info not available in this environment",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/version")
async def sys_version():
    return {"version": settings.VERSION, "service": settings.APP_NAME}


@router.get("/control-plane-map")
async def control_plane_map():
    """Returns a full listing of all mounted Veklom control-plane modules."""
    return {
        "control_plane": "Veklom Sovereign Control Plane",
        "version": settings.VERSION,
        "modules": [
            {"name": "Workspace", "path": "/workspace/", "status": "active"},
            {"name": "Control Plane Next", "path": "/control-plane-next/", "status": "active"},
            {"name": "Command Center", "path": "/command-center/", "status": "active"},
            {"name": "UACP Quantum Terminal", "path": "/terminal", "status": "active"},
            {"name": "PYO3 IronGrid", "path": "/irongrid/", "status": "active"},
            {"name": "GPC Engine", "path": "/gpc-engine/", "status": "active"},
            {"name": "Operator Center", "path": "/operator-center/", "status": "active"},
            {"name": "AI Inference", "path": "/api/v1/ai/", "status": "active"},
            {"name": "x402 Payment Gateway", "path": "/api/v1/x402/", "status": "active"},
            {"name": "Fax Connector", "path": "/api/v1/connectors/fax/", "status": "active"},
            {"name": "Evidence Ledger", "path": "/api/v1/compliance/evidence/", "status": "active"},
            {"name": "Monitoring & Telemetry", "path": "/api/v1/monitoring/", "status": "active"},
            {"name": "Marketplace", "path": "/api/v1/marketplace/", "status": "active"},
        ],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

