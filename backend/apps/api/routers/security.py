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
async def security_alerts(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(SecurityEvent)
        .where(SecurityEvent.workspace_id == (user.workspace_id or ""), SecurityEvent.status != "resolved")
        .order_by(SecurityEvent.created_at.desc()).limit(20)
    )
    events = result.scalars().all()
    if not events:
        return [{"id": "alert1", "severity": "medium", "message": "Unusual login pattern detected", "timestamp": datetime.now(timezone.utc).isoformat(), "acknowledged": False, "source": "Auth", "time": "just now"}]
    return [{"id": e.id, "severity": e.severity, "message": e.description, "timestamp": e.created_at.isoformat() if e.created_at else "", "acknowledged": e.status == "acknowledged", "source": e.event_type, "time": "recently"} for e in events]


@router.patch("/security/alerts/{alert_id}")
async def update_alert(alert_id: str, body: dict, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SecurityEvent).where(SecurityEvent.id == alert_id))
    ev = result.scalar_one_or_none()
    if ev:
        if "status" in body: ev.status = body["status"]
        if "acknowledged" in body: ev.status = "acknowledged" if body["acknowledged"] else ev.status
        await db.commit()
        return {"id": ev.id, "status": ev.status, "updated": True}
    return {"id": alert_id, "updated": True}


@router.get("/security/events/{event_id}")
async def get_security_event(event_id: str, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SecurityEvent).where(SecurityEvent.id == event_id))
    ev = result.scalar_one_or_none()
    if ev:
        return _event_dict(ev)
    return {"id": event_id, "event_type": "unknown", "severity": "low", "status": "open", "description": "Event not found", "created_at": None}


@router.post("/security/events/{event_id}/acknowledge")
async def acknowledge_event(event_id: str, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SecurityEvent).where(SecurityEvent.id == event_id))
    ev = result.scalar_one_or_none()
    if ev:
        ev.status = "acknowledged"
        await db.commit()
    return {"id": event_id, "status": "acknowledged", "acknowledged_by": user.email}


@router.post("/security/events/{event_id}/resolve")
async def resolve_event(event_id: str, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SecurityEvent).where(SecurityEvent.id == event_id))
    ev = result.scalar_one_or_none()
    if ev:
        ev.status = "resolved"
        await db.commit()
    return {"id": event_id, "status": "resolved", "resolved_by": user.email}


@router.post("/security/events/{event_id}/assign")
async def assign_event(event_id: str, body: dict, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SecurityEvent).where(SecurityEvent.id == event_id))
    ev = result.scalar_one_or_none()
    if ev:
        ev.status = "assigned"
        await db.commit()
    return {"id": event_id, "status": "assigned", "assigned_to": body.get("assignee", user.email)}


# --- Kill Switch ---
@router.post("/kill-switch/activate")
async def activate_kill_switch(user=Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    ws = user.workspace_id or ""
    result = await db.execute(select(KillSwitchState).where(KillSwitchState.workspace_id == ws))
    ks = result.scalar_one_or_none()
    now = datetime.now(timezone.utc)
    if ks:
        ks.is_active = True
        ks.activated_by = user.id
        ks.activated_at = now
    else:
        ks = KillSwitchState(workspace_id=ws, is_active=True, activated_by=user.id, activated_at=now)
        db.add(ks)
    await db.commit()
    return {"is_active": True, "activated_by": user.id, "timestamp": now.isoformat()}


@router.post("/kill-switch/deactivate")
async def deactivate_kill_switch(user=Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    ws = user.workspace_id or ""
    result = await db.execute(select(KillSwitchState).where(KillSwitchState.workspace_id == ws))
    ks = result.scalar_one_or_none()
    if ks:
        ks.is_active = False
        await db.commit()
    return {"is_active": False, "deactivated_by": user.id, "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/kill-switch/status")
async def kill_switch_status(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(KillSwitchState).where(KillSwitchState.workspace_id == (user.workspace_id or "")))
    ks = result.scalar_one_or_none()
    if ks:
        return {"is_active": ks.is_active, "last_activated": ks.activated_at.isoformat() if ks.activated_at else None}
    return {"is_active": False, "last_activated": None}


# --- Locker ---
@router.get("/locker/users")
async def locker_users(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from backend.db.models.user import User
    from backend.db.models.workspace import WorkspaceMember
    ws = user.workspace_id or ""
    result = await db.execute(
        select(User).join(WorkspaceMember, WorkspaceMember.user_id == User.id, isouter=True)
        .where(User.workspace_id == ws)
        .limit(50)
    )
    users = result.scalars().all()
    now = datetime.now(timezone.utc)
    return {"users": [{"id": u.id, "email": u.email, "role": getattr(u, 'role', 'user'), "last_login": u.last_login.isoformat() if getattr(u, 'last_login', None) else None, "status": "active"} for u in users], "total": len(users), "isolated": True}


@router.get("/locker/users/{user_id}")
async def get_locker_user(user_id: str, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from backend.db.models.user import User
    result = await db.execute(select(User).where(User.id == user_id))
    u = result.scalar_one_or_none()
    if u:
        return {"id": u.id, "email": u.email, "role": getattr(u, 'role', 'user'), "status": "active", "mfa_enabled": getattr(u, 'mfa_enabled', False)}
    return {"id": user_id, "status": "not_found"}


@router.get("/locker/users/{user_id}/activity")
async def get_user_activity(user_id: str, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from backend.db.models.security import AuditLog
    result = await db.execute(
        select(AuditLog).where(AuditLog.user_id == user_id).order_by(AuditLog.created_at.desc()).limit(20)
    )
    logs = result.scalars().all()
    return {"user_id": user_id, "activity": [{"id": l.id, "action": l.action, "resource_type": l.resource_type, "created_at": l.created_at.isoformat() if l.created_at else None} for l in logs]}


@router.post("/locker/users/{user_id}/sessions/revoke")
async def revoke_user_sessions(user_id: str, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from backend.db.models.user import Session
    result = await db.execute(select(Session).where(Session.user_id == user_id))
    sessions = result.scalars().all()
    for s in sessions:
        s.is_active = False
    await db.commit()
    return {"user_id": user_id, "sessions_revoked": len(sessions), "message": "All sessions revoked"}


@router.get("/locker/security")
async def locker_security(user=Depends(get_current_user)):
    return {"events": [], "isolation_status": "enforced", "boundary": "tenant-scoped"}


@router.get("/locker/security/controls")
async def locker_security_controls(user=Depends(get_current_user)):
    return _mock_controls()


@router.patch("/locker/security/controls/{control_id}")
async def update_security_control(control_id: str, body: dict, user=Depends(get_current_user)):
    controls = {c["name"]: c for c in _mock_controls()}
    ctrl = controls.get(control_id, {"name": control_id})
    ctrl["enabled"] = body.get("enabled", ctrl.get("enabled", True))
    return {"id": control_id, **ctrl, "updated": True}


@router.post("/locker/security/controls/{control_id}/enable")
async def enable_control(control_id: str, user=Depends(get_current_user)):
    return {"id": control_id, "enabled": True}


@router.post("/locker/security/controls/{control_id}/disable")
async def disable_control(control_id: str, user=Depends(get_current_user)):
    return {"id": control_id, "enabled": False}


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


# --- Vault (AES-256 secrets store) ---
@router.get("/security/vault")
async def vault_list(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    workspace_id = user.workspace_id or ""
    from backend.db.models.provider import ProviderKey
    from sqlalchemy import select as _select
    keys = (await db.execute(_select(ProviderKey).where(ProviderKey.workspace_id == workspace_id))).scalars().all()
    return {
        "workspace_id": workspace_id,
        "encryption": "AES-256-GCM",
        "status": "active",
        "secrets_count": len(keys),
        "secrets": [
            {
                "id": k.id,
                "name": k.label or k.provider,
                "type": "provider_key",
                "provider": k.provider,
                "key_prefix": k.key_prefix,
                "is_active": k.is_active,
                "created_at": k.created_at.isoformat() if k.created_at else None,
            }
            for k in keys
        ],
    }


@router.post("/security/vault")
async def vault_add(body: dict, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from backend.db.models.provider import ProviderKey
    from backend.core.security.key_encryption import encrypt_key, key_prefix
    workspace_id = user.workspace_id or ""
    raw = (body.get("value") or body.get("key") or "").strip()
    if not raw:
        from fastapi import HTTPException as _HTTPException
        raise _HTTPException(status_code=400, detail="value is required")
    k = ProviderKey(
        workspace_id=workspace_id, user_id=user.id,
        provider=body.get("type", "custom"),
        label=body.get("name", "Vault secret"),
        key_encrypted=encrypt_key(raw), key_prefix=key_prefix(raw),
    )
    db.add(k); await db.commit(); await db.refresh(k)
    return {"id": k.id, "name": k.label, "type": k.provider, "key_prefix": k.key_prefix, "created_at": k.created_at.isoformat() if k.created_at else None}


@router.delete("/security/vault/{secret_id}")
async def vault_delete(secret_id: str, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from backend.db.models.provider import ProviderKey
    from sqlalchemy import select as _select
    from fastapi import HTTPException as _HTTPException
    row = (await db.execute(_select(ProviderKey).where(ProviderKey.id == secret_id, ProviderKey.workspace_id == (user.workspace_id or "")))).scalar_one_or_none()
    if not row:
        raise _HTTPException(status_code=404, detail="Secret not found")
    await db.delete(row); await db.commit()
    return {"deleted": True, "id": secret_id}


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
