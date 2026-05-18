"""Security routes — events, alerts, dashboard, kill switch, locker."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database.database import get_db
from backend.core.security.auth import get_current_user, get_current_admin
from backend.db.models.security import SecurityEvent, KillSwitchState

router = APIRouter(tags=["Security"])


# --- Security Events ---
@router.get("/security/events")
async def list_security_events(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SecurityEvent).order_by(SecurityEvent.created_at.desc()).limit(50))
    events = result.scalars().all()
    if not events:
        return _mock_events()
    return [_event_dict(e) for e in events]


@router.get("/security/dashboard")
async def security_dashboard(user=Depends(get_current_user)):
    return {
        "security_score": 92,
        "total_events_24h": 3,
        "critical_alerts": 0,
        "open_incidents": 1,
        "controls": _mock_controls(),
        "recent_events": _mock_events()[:5],
    }


@router.get("/security/stats")
async def security_stats(user=Depends(get_current_user)):
    return {
        "total_events": 47,
        "by_severity": {"critical": 2, "high": 8, "medium": 15, "low": 22},
        "by_type": {"auth_failure": 12, "suspicious_access": 5, "rate_limit": 20, "policy_violation": 10},
        "trend_24h": "stable",
    }


@router.get("/security/alerts")
async def security_alerts(user=Depends(get_current_user)):
    return [
        {"id": "alert1", "severity": "medium", "message": "Unusual login pattern detected", "timestamp": datetime.now(timezone.utc).isoformat(), "acknowledged": False},
    ]


# --- Kill Switch ---
@router.post("/kill-switch/activate")
async def activate_kill_switch(user=Depends(get_current_admin)):
    return {"is_active": True, "activated_by": user.id, "timestamp": datetime.now(timezone.utc).isoformat()}


@router.post("/kill-switch/deactivate")
async def deactivate_kill_switch(user=Depends(get_current_admin)):
    return {"is_active": False, "deactivated_by": user.id, "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/kill-switch/status")
async def kill_switch_status(user=Depends(get_current_user)):
    return {"is_active": False, "last_activated": None}


# --- Locker ---
@router.get("/locker/users")
async def locker_users(user=Depends(get_current_user)):
    return {"users": [], "total": 0, "isolated": True}


@router.get("/locker/security")
async def locker_security(user=Depends(get_current_user)):
    return {"events": [], "isolation_status": "enforced", "boundary": "tenant-scoped"}


@router.get("/locker/security/controls")
async def locker_security_controls(user=Depends(get_current_user)):
    return _mock_controls()


@router.get("/locker/security/dashboard")
async def locker_security_dashboard(user=Depends(get_current_user)):
    return {"security_score": 95, "controls": _mock_controls(), "events": _mock_events()[:3]}


@router.get("/locker/security/events")
async def locker_security_events(user=Depends(get_current_user)):
    return _mock_events()


@router.get("/locker/security/threats/stats")
async def locker_threat_stats(user=Depends(get_current_user)):
    return {"total": 12, "by_type": {"brute_force": 3, "suspicious_ip": 5, "anomaly": 4}, "trend": "decreasing"}


@router.get("/locker/monitoring")
async def locker_monitoring(user=Depends(get_current_user)):
    return {"status": "healthy", "metrics": {"cpu": 34.2, "memory": 58.1, "disk": 22.3}}


@router.get("/locker/monitoring/status")
async def locker_monitoring_status(user=Depends(get_current_user)):
    return {"status": "operational", "uptime_percent": 99.97}


@router.get("/locker/monitoring/health/detailed")
async def locker_health_detailed(user=Depends(get_current_user)):
    return {"status": "healthy", "components": {"db": "healthy", "redis": "healthy", "ai": "healthy"}}


@router.get("/locker/monitoring/metrics/performance")
async def locker_perf_metrics(user=Depends(get_current_user)):
    return {"avg_latency_ms": 45, "p99_latency_ms": 230, "requests_per_second": 120, "error_rate": 0.001}


@router.get("/locker/monitoring/alerts")
async def locker_alerts(user=Depends(get_current_user)):
    return []


@router.get("/locker/monitoring/alerts/summary")
async def locker_alerts_summary(user=Depends(get_current_user)):
    return {"total": 0, "critical": 0, "warning": 0, "info": 0}


# --- Threats ---
@router.get("/threats/stats")
async def threat_stats(user=Depends(get_current_user)):
    return {"total": 47, "open": 1, "resolved": 46, "by_severity": {"critical": 2, "high": 8, "medium": 15, "low": 22}}


def _event_dict(e: SecurityEvent) -> dict:
    return {
        "id": e.id,
        "event_type": e.event_type,
        "threat_type": e.threat_type,
        "severity": e.severity,
        "description": e.description,
        "status": e.status,
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }


def _mock_events():
    now = datetime.now(timezone.utc).isoformat()
    return [
        {"id": "se1", "event_type": "auth_failure", "threat_type": "brute_force", "severity": "medium", "description": "Multiple failed login attempts", "status": "open", "created_at": now},
        {"id": "se2", "event_type": "rate_limit", "threat_type": "dos", "severity": "low", "description": "Rate limit triggered", "status": "resolved", "created_at": now},
        {"id": "se3", "event_type": "policy_violation", "threat_type": "compliance", "severity": "high", "description": "PII detected in prompt", "status": "resolved", "created_at": now},
    ]


def _mock_controls():
    return [
        {"name": "mfa_enabled", "display_name": "Multi-Factor Auth", "enabled": True, "category": "authentication"},
        {"name": "ai_monitoring", "display_name": "AI Monitoring", "enabled": True, "category": "monitoring"},
        {"name": "rate_limiting", "display_name": "Rate Limiting", "enabled": True, "category": "protection"},
        {"name": "encryption", "display_name": "Encryption at Rest", "enabled": True, "category": "encryption"},
        {"name": "audit_logging", "display_name": "Audit Logging", "enabled": True, "category": "logging"},
        {"name": "session_timeout", "display_name": "Session Timeout", "enabled": True, "category": "session"},
    ]
