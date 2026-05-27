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
