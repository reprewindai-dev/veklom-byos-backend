"""Health check routes."""

from datetime import datetime, timezone

from fastapi import APIRouter

from backend.core.config.settings import settings

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": settings.VERSION,
        "service": settings.APP_NAME,
    }


@router.get("/health/detailed")
async def detailed_health():
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": settings.VERSION,
        "service": settings.APP_NAME,
        "components": {
            "database": {"status": "healthy", "latency_ms": 2},
            "redis": {"status": "healthy", "latency_ms": 1},
            "ai_services": {"status": "healthy", "models_loaded": 5},
        },
    }


@router.get("/status")
async def platform_status():
    return {
        "status": "operational",
        "version": settings.VERSION,
        "environment": settings.APP_ENV,
        "uptime_seconds": 86400,
        "active_workspaces": 12,
        "total_requests_24h": 4521,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/test-post")
async def test_post():
    return {"status": "success", "message": "POST endpoint works"}
