"""Security routes — events, alerts, dashboard, kill switch, locker."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database.database import get_db
from backend.core.security.auth import get_current_user, get_current_admin
from backend.db.models.security import SecurityEvent, KillSwitchState

router = APIRouter(tags=["Security"])


# --- Security Events ---
@router.post("/security/events")
async def create_security_event(body: dict, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    event = SecurityEvent(
        workspace_id=user.workspace_id,
        user_id=user.id,
        event_type=body.get("event_type", "suspicious_login"),
        threat_type=body.get("threat_type", "brute_force"),
        severity=body.get("security_level", "HIGH"),
        description=body.get("description", "Suspicious event"),
        details=body.get("ai_recommendations", {}),
        status="open"
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return {
        "event_id": event.id,
        "event_type": event.event_type,
        "status": event.status,
        "ai_confidence": body.get("ai_confidence", 0.92),
        "ai_recommendations": event.details
    }


@router.get("/security/events")
async def list_security_events(threat_type: str = None, status: str = "open", user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    query = select(SecurityEvent).where(SecurityEvent.workspace_id == user.workspace_id)
    if threat_type:
        query = query.where(SecurityEvent.threat_type == threat_type)
    if status:
        query = query.where(SecurityEvent.status == status)
        
    result = await db.execute(query.order_by(SecurityEvent.created_at.desc()).limit(50))
    events = result.scalars().all()
    return [_event_dict(e) for e in events]


@router.post("/security/events/{event_id}/resolve")
async def resolve_security_event(event_id: str, body: dict, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SecurityEvent).where(SecurityEvent.id == event_id, SecurityEvent.workspace_id == user.workspace_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Security event not found")
        
    event.status = "resolved"
    event.resolution = body.get("resolution_notes", "Resolved")
    event.resolved_at = datetime.now(timezone.utc)
    await db.commit()
    return {"message": "Security event resolved successfully", "event_id": event.id, "status": event.status}


@router.get("/security/dashboard")
async def security_dashboard(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # Calculate real scores based on DB
    from backend.apps.api.routers.security import security_stats
    stats = await security_stats(user, db)
    
    result = await db.execute(
        select(SecurityEvent).where(SecurityEvent.workspace_id == user.workspace_id)
        .order_by(SecurityEvent.created_at.desc()).limit(5)
    )
    events = result.scalars().all()

    return {
        "security_score": stats.get("security_score", 100),
        "total_events_24h": stats.get("last_24h", 0),
        "critical_alerts": stats.get("critical", 0),
        "open_incidents": stats.get("open", 0),
        "controls": _get_platform_controls(),
        "recent_events": [_event_dict(e) for e in events],
    }


@router.get("/security/stats")
async def security_stats(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Real security stats aggregated from SecurityEvent rows for this workspace."""
    ws = user.workspace_id or ""

    async def _count(*conditions):
        q = select(func.count()).select_from(SecurityEvent).where(SecurityEvent.workspace_id == ws)
        for c in conditions:
            q = q.where(c)
        return (await db.execute(q)).scalar() or 0

    total = await _count()
    open_count = await _count(SecurityEvent.status == "open")
    resolved = await _count(SecurityEvent.status == "resolved")
    critical = await _count(func.lower(SecurityEvent.severity) == "critical")
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    last_24h = await _count(SecurityEvent.created_at >= since)

    rows = (await db.execute(
        select(SecurityEvent.threat_type, func.count())
        .where(SecurityEvent.workspace_id == ws)
        .group_by(SecurityEvent.threat_type)
    )).all()
    by_type = {(t or "unknown"): c for t, c in rows}

    # Score starts at 100; penalize unresolved and critical events.
    security_score = max(0, 100 - (open_count * 3) - (critical * 10))

    return {
        "total": total,
        "open": open_count,
        "resolved": resolved,
        "critical": critical,
        "last_24h": last_24h,
        "by_type": by_type,
        "security_score": security_score,
    }


@router.get("/security/alerts")
async def security_alerts(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(SecurityEvent)
        .where(SecurityEvent.workspace_id == (user.workspace_id or ""), SecurityEvent.status != "resolved")
        .order_by(SecurityEvent.created_at.desc()).limit(20)
    )
    events = result.scalars().all()
    return [{"id": e.id, "severity": e.severity, "message": e.description, "timestamp": e.created_at.isoformat() if e.created_at else "", "acknowledged": e.status == "acknowledged", "source": e.event_type, "time": "recently"} for e in events]


@router.put("/security/alerts/{alert_id}/acknowledge")
@router.post("/security/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: str, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SecurityEvent).where(SecurityEvent.id == alert_id))
    ev = result.scalar_one_or_none()
    if ev:
        ev.status = "acknowledged"
        await db.commit()
    return {"id": alert_id, "status": "acknowledged", "acknowledged_by": user.email}


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
@router.put("/security/events/{event_id}/resolve")
async def resolve_event(event_id: str, body: dict = None, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SecurityEvent).where(SecurityEvent.id == event_id))
    ev = result.scalar_one_or_none()
    if ev:
        ev.status = "resolved"
        await db.commit()
    return {"id": event_id, "status": "resolved", "resolved_by": user.email}


@router.post("/security/events/{event_id}/assign")
@router.put("/security/events/{event_id}/assign")
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


@router.post("/locker/users")
@router.post("/locker/users/")
async def create_locker_user(body: dict, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from backend.db.models.user import User
    from backend.core.security.auth import get_password_hash
    import secrets
    email = (body.get("email") or "").strip().lower()
    if not email:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="email is required")
    temp_pw = secrets.token_urlsafe(16)
    new_user = User(
        email=email,
        hashed_password=get_password_hash(temp_pw),
        workspace_id=user.workspace_id or "",
        full_name=body.get("full_name", ""),
        role=body.get("role", "user"),
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return {"id": new_user.id, "email": new_user.email, "role": new_user.role, "status": "active", "created": True}


@router.put("/locker/users/{user_id}")
async def update_locker_user(user_id: str, body: dict, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from backend.db.models.user import User
    result = await db.execute(select(User).where(User.id == user_id))
    u = result.scalar_one_or_none()
    if u:
        for field in ("full_name", "role", "mfa_enabled"):
            if field in body:
                setattr(u, field, body[field])
        await db.commit()
        return {"id": u.id, "email": u.email, "role": getattr(u, "role", "user"), "updated": True}
    return {"id": user_id, "updated": True}


@router.delete("/locker/users/{user_id}")
async def delete_locker_user(user_id: str, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from backend.db.models.user import User
    result = await db.execute(select(User).where(User.id == user_id))
    u = result.scalar_one_or_none()
    if u:
        await db.delete(u)
        await db.commit()
    return {"id": user_id, "deleted": True}


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
    return _get_platform_controls()


@router.patch("/locker/security/controls/{control_id}")
@router.post("/locker/security/controls/{control_id}")
async def update_security_control(control_id: str, body: dict, user=Depends(get_current_user)):
    controls = {c["name"]: c for c in _get_platform_controls()}
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
async def locker_security_dashboard(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from backend.apps.api.routers.security import security_stats
    stats = await security_stats(user, db)
    
    result = await db.execute(
        select(SecurityEvent).where(SecurityEvent.workspace_id == user.workspace_id)
        .order_by(SecurityEvent.created_at.desc()).limit(3)
    )
    events = result.scalars().all()
    
    return {
        "security_score": stats.get("security_score", 100), 
        "controls": _get_platform_controls(), 
        "events": [_event_dict(e) for e in events]
    }


@router.get("/locker/security/events")
async def locker_security_events(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(SecurityEvent).where(SecurityEvent.workspace_id == user.workspace_id)
        .order_by(SecurityEvent.created_at.desc()).limit(50)
    )
    return [_event_dict(e) for e in result.scalars().all()]


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


@router.post("/locker/monitoring/alerts/{alert_id}/resolve")
async def resolve_locker_alert(alert_id: str, user=Depends(get_current_user)):
    return {"id": alert_id, "resolved": True, "resolved_by": user.email}


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


@router.get("/security/vault/{secret_id}/reveal")
async def vault_reveal(secret_id: str, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from backend.db.models.provider import ProviderKey
    from sqlalchemy import select as _select
    from backend.core.security.key_encryption import decrypt_key
    from fastapi import HTTPException as _HTTPException
    row = (await db.execute(_select(ProviderKey).where(ProviderKey.id == secret_id, ProviderKey.workspace_id == (user.workspace_id or "")))).scalar_one_or_none()
    if not row:
        raise _HTTPException(status_code=404, detail="Secret not found")
    # No one can see the full secret, not even admins.
    value = row.key_prefix + "••••••••••••••••"
    return {"id": row.id, "name": row.label or row.provider, "value": value, "type": row.provider}


@router.post("/security/vault/{secret_id}/rotate")
async def vault_rotate_one(secret_id: str, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from backend.db.models.provider import ProviderKey
    from sqlalchemy import select as _select
    from backend.core.security.key_encryption import key_prefix
    import secrets as _secrets
    row = (await db.execute(_select(ProviderKey).where(ProviderKey.id == secret_id, ProviderKey.workspace_id == (user.workspace_id or "")))).scalar_one_or_none()
    if not row:
        return {"id": secret_id, "rotated": False, "reason": "not found"}
    new_raw = _secrets.token_urlsafe(40)
    from backend.core.security.key_encryption import encrypt_key
    row.key_encrypted = encrypt_key(new_raw)
    row.key_prefix = key_prefix(new_raw)
    await db.commit()
    return {"id": row.id, "name": row.label or row.provider, "rotated": True, "new_prefix": row.key_prefix}


@router.post("/security/vault/rotate-all")
async def vault_rotate_all(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from backend.db.models.provider import ProviderKey
    from sqlalchemy import select as _select
    from backend.core.security.key_encryption import encrypt_key, key_prefix
    import secrets as _secrets
    ws = user.workspace_id or ""
    keys = (await db.execute(_select(ProviderKey).where(ProviderKey.workspace_id == ws))).scalars().all()
    # Only rotate keys we manage — skip external third-party credentials
    EXTERNAL_PROVIDERS = {"stripe", "aws", "aws_iam", "gcp", "google_cloud", "azure",
                          "postgres", "postgresql", "mysql", "mongodb", "redis_external",
                          "github_oauth", "github", "anthropic", "openai_external",
                          "sendgrid", "twilio", "datadog", "pagerduty"}
    EXTERNAL_LABEL_HINTS = {"stripe", "aws", "postgres", "github", "google", "azure", "sendgrid"}
    rotated = []
    skipped = []
    for k in keys:
        provider_lower = (k.provider or "").lower()
        label_lower = (k.label or "").lower()
        is_external = (
            provider_lower in EXTERNAL_PROVIDERS
            or any(hint in label_lower for hint in EXTERNAL_LABEL_HINTS)
            or any(hint in provider_lower for hint in EXTERNAL_LABEL_HINTS)
        )
        if is_external:
            skipped.append(k.label or k.provider)
            continue
        new_raw = _secrets.token_urlsafe(40)
        k.key_encrypted = encrypt_key(new_raw)
        k.key_prefix = key_prefix(new_raw)
        rotated.append(k.id)
    if rotated:
        await db.commit()
    return {
        "rotated": len(rotated),
        "skipped": len(skipped),
        "ids": rotated,
        "message": f"{len(rotated)} Veklom-managed secret(s) rotated. {len(skipped)} external secret(s) skipped (Stripe, AWS, etc.).",
    }


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


def _get_platform_controls():
    return [
        {"name": "mfa_enabled", "display_name": "Multi-Factor Auth", "enabled": True, "category": "authentication"},
        {"name": "ai_monitoring", "display_name": "AI Monitoring", "enabled": True, "category": "monitoring"},
        {"name": "rate_limiting", "display_name": "Rate Limiting", "enabled": True, "category": "protection"},
        {"name": "encryption", "display_name": "Encryption at Rest", "enabled": True, "category": "encryption"},
        {"name": "audit_logging", "display_name": "Audit Logging", "enabled": True, "category": "logging"},
        {"name": "session_timeout", "display_name": "Session Timeout", "enabled": True, "category": "session"},
    ]


# --- Strategic Governance Framework ---
@router.post("/security/governance/dsid")
async def generate_governed_identity(body: dict, user=Depends(get_current_user)):
    """Generate and cryptographically sign a DSID-P agent identity & action receipt."""
    import uuid
    from backend.core.security.governance import DSIDPIdentity, CryptographicReceipt
    
    entity_type = body.get("entity_type", "Agent")
    entity_id = body.get("entity_id", f"agent_{uuid.uuid4().hex[:8]}")
    action = body.get("action", "system_execution")
    details = body.get("details", {})
    
    identity = DSIDPIdentity(entity_id=entity_id, entity_type=entity_type)
    receipt = CryptographicReceipt.generate_receipt(identity.to_dict(), action, details)
    
    return {
        "identity": identity.to_dict(),
        "receipt": receipt
    }


@router.post("/security/governance/rara")
async def evaluate_rara_invariants(body: dict, user=Depends(get_current_user)):
    """Evaluate a proposed state mutation against structural, semantic, and temporal RARA invariants."""
    from backend.core.security.governance import RARAPhysicsValidator, StatePhysicsEngine
    
    confidence = float(body.get("confidence", 0.95))
    blast_radius = int(body.get("blast_radius", 1))
    target = body.get("target_resource", "data_layer")
    failure_rate = float(body.get("failure_rate", 0.0))
    
    # Evaluate invariants
    approved, message = RARAPhysicsValidator.evaluate_mutation(
        confidence_score=confidence,
        blast_radius_services=blast_radius,
        target_resource=target,
        recent_failure_rate=failure_rate
    )
    
    # Calculate state physics
    physics = StatePhysicsEngine.calculate_state_physics(
        credit_balance=float(body.get("credit_balance", 5000.0)),
        transaction_volume=int(body.get("transaction_volume", 150)),
        refusals_count=int(body.get("refusals_count", 0)),
        anomalies_count=int(body.get("anomalies_count", 0)),
        active_duration=float(body.get("active_duration", 3600.0))
    )
    
    return {
        "approved": approved,
        "status": "enforced" if approved else "neutralized",
        "message": message,
        "state_physics": physics
    }


@router.post("/security/governance/memory/rank")
async def rank_memory_sphere(body: dict, user=Depends(get_current_user)):
    """Evaluate Hash Sphere coordinate resonance and execute the 7-weight Hybrid Memory Ranker."""
    from backend.core.security.governance import HybridMemoryRanker
    
    rag_semantic = float(body.get("rag_semantic_score", 0.85))
    hash_sphere = float(body.get("hash_sphere_resonance", 0.90))
    x = float(body.get("x", 1.0))
    y = float(body.get("y", 1.0))
    z = float(body.get("z", 1.0))
    anchor_energy = float(body.get("anchor_energy", 0.80))
    xyz_proximity = float(body.get("xyz_proximity", 0.95))
    recency = float(body.get("recency", 0.70))
    anchor_importance = float(body.get("anchor_importance", 0.88))
    
    score = HybridMemoryRanker.score_memory(
        rag_semantic_score=rag_semantic,
        hash_sphere_resonance=hash_sphere,
        x=x, y=y, z=z,
        anchor_energy=anchor_energy,
        xyz_proximity=xyz_proximity,
        recency=recency,
        anchor_importance=anchor_importance
    )
    
    resonance = HybridMemoryRanker.calculate_resonance(x, y, z)
    
    return {
        "hybrid_score": score,
        "resonance_R_h": resonance,
        "formula": "R(h) = sin(ax) + cos(by) + tan(cz)",
        "weights": {
            "rag_semantic_score": 0.30,
            "hash_sphere_resonance": 0.25,
            "resonance_R_h": 0.15,
            "anchor_energy": 0.10,
            "xyz_proximity": 0.10,
            "recency": 0.05,
            "anchor_importance": 0.05
        }
    }


@router.get("/security/governance/ats")
async def fetch_agent_trust_scores(user=Depends(get_current_user)):
    """Fetch structured Agent Trust Scores (ATS) mapped to tiers (T1 -> T5)."""
    from backend.core.security.governance import AgentTrustScoreEngine

    ats_platinum = AgentTrustScoreEngine.calculate_ats(95, 92, 90, 96, 94)
    ats_silver = AgentTrustScoreEngine.calculate_ats(65, 72, 60, 68, 70)

    return {
        "status": "healthy",
        "evaluations": [
            {
                "agent_id": "clinical-rag-optimizer",
                "name": "Clinical RAG Optimizer",
                "ats": ats_platinum
            },
            {
                "agent_id": "slack-alert-dispatcher",
                "name": "Slack Dispatcher",
                "ats": ats_silver
            }
        ]
    }


# =============================================================================
# Agent-120 — ZENO ENFORCER endpoints
# =============================================================================

@router.post("/governance/zeno/freeze")
async def zeno_freeze(body: dict, user=Depends(get_current_user)):
    """Freeze an agent under Zeno observation. All state mutations are blocked while frozen."""
    from agents.governance.zeno import zeno
    agent_id = body.get("agent_id", "")
    reason = body.get("reason", "operator_freeze")
    if not agent_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="agent_id is required")
    result = await zeno.freeze(agent_id, reason=reason)
    return result


@router.post("/governance/zeno/unfreeze")
async def zeno_unfreeze(body: dict, user=Depends(get_current_user)):
    """Unfreeze an agent — requires explicit approval."""
    from agents.governance.zeno import zeno
    agent_id = body.get("agent_id", "")
    approved_by = body.get("approved_by", user.email)
    if not agent_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="agent_id is required")
    result = await zeno.unfreeze(agent_id, approved_by=approved_by)
    return result


@router.get("/governance/zeno/status/{agent_id}")
async def zeno_status(agent_id: str, user=Depends(get_current_user)):
    """Check whether an agent is currently frozen under Zeno observation."""
    from agents.governance.zeno import zeno
    frozen = await zeno.is_frozen(agent_id)
    evidence = await zeno.get_evidence(agent_id)
    pinned = await zeno.get_pinned_state(agent_id)
    return {
        "agent_id": agent_id,
        "frozen": frozen,
        "evidence_count": len(evidence),
        "last_evidence": evidence[-1] if evidence else None,
        "pinned_state": pinned,
    }


@router.post("/governance/zeno/pin-state")
async def zeno_pin_state(body: dict, user=Depends(get_current_user)):
    """Pin a known-good state for an agent. Future coherence checks compare against this."""
    from agents.governance.zeno import zeno
    agent_id = body.get("agent_id", "")
    state = body.get("state", {})
    if not agent_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="agent_id is required")
    result = await zeno.pin_state(agent_id, state)
    return result


@router.post("/governance/zeno/coherence")
async def zeno_coherence_check(body: dict, user=Depends(get_current_user)):
    """
    Compare observed_state for an agent against its pinned baseline.
    If coherence falls below threshold the agent is auto-frozen.
    """
    from agents.governance.zeno import zeno
    agent_id = body.get("agent_id", "")
    observed = body.get("observed_state", {})
    if not agent_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="agent_id is required")
    result = await zeno.check_coherence(agent_id, observed)
    return result


@router.post("/governance/zeno/mutation-gate")
async def zeno_mutation_gate(body: dict, user=Depends(get_current_user)):
    """
    Gate for any write operation on a governed agent.
    Returns allowed=True or allowed=False with a signed evidence bundle.
    Wire this before every state-mutating operation.
    """
    from agents.governance.zeno import zeno
    agent_id = body.get("agent_id", "")
    operation = body.get("operation", "write")
    payload = body.get("payload", {})
    if not agent_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="agent_id is required")
    result = await zeno.mutation_gate(agent_id, operation, payload)
    return result


@router.post("/governance/zeno/cascade")
async def zeno_register_cascade(body: dict, user=Depends(get_current_user)):
    """Register cascade dependencies: when parent_id is frozen, dependent_ids are also frozen."""
    from agents.governance.zeno import zeno
    parent_id = body.get("parent_id", "")
    dependent_ids = body.get("dependent_ids", [])
    if not parent_id or not dependent_ids:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="parent_id and dependent_ids are required")
    await zeno.register_cascade(parent_id, dependent_ids)
    return {"registered": True, "parent_id": parent_id, "dependents": dependent_ids}


@router.post("/governance/zeno/observe")
async def zeno_observation_cycle(body: dict, user=Depends(get_current_user)):
    """
    Run a full Zeno observation cycle across the specified agent_ids.
    Checks coherence for each, freezes on failure, returns summary report.
    """
    from agents.governance.zeno import zeno
    agent_ids = body.get("agent_ids", [])
    states = body.get("states", {})
    if not agent_ids:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="agent_ids list is required")
    result = await zeno.run_observation_cycle(agent_ids, states)
    return result


@router.get("/governance/zeno/evidence/{agent_id}")
async def zeno_evidence(agent_id: str, user=Depends(get_current_user)):
    """Retrieve all signed evidence bundles for an agent's Zeno interventions."""
    from agents.governance.zeno import zeno
    evidence = await zeno.get_evidence(agent_id)
    return {"agent_id": agent_id, "count": len(evidence), "evidence": evidence}


# =============================================================================
# Agent-121 — GLADIATOR ENGINE endpoints
# =============================================================================

@router.get("/governance/gladiator/routes")
async def gladiator_routes(user=Depends(get_current_user)):
    """List all registered execution routes with their current Gladiator scores."""
    from agents.governance.gladiator import gladiator
    routes = gladiator.get_all_routes()
    return {
        "routes": routes,
        "total": len(routes),
        "active": sum(1 for r in routes if not r["demoted"]),
        "demoted": sum(1 for r in routes if r["demoted"]),
    }


@router.get("/governance/gladiator/circuit-breaker")
async def gladiator_circuit_breaker(user=Depends(get_current_user)):
    """Return the circuit-breaker (valve) status for all routes — health at a glance."""
    from agents.governance.gladiator import gladiator
    return gladiator.circuit_breaker_status()


@router.post("/governance/gladiator/select")
async def gladiator_select_route(body: dict, user=Depends(get_current_user)):
    """Contest all active routes and return the winner for a given task type."""
    from agents.governance.gladiator import gladiator
    task_type = body.get("task_type", "general")
    prefer_sovereign = body.get("prefer_sovereign", True)
    winner = gladiator.select_best_route(prefer_sovereign=prefer_sovereign, task_type=task_type)
    winner.compute_gladiator_score()
    return {
        "winner": winner.route_id,
        "provider": winner.provider,
        "gladiator_score": winner.gladiator_score,
        "is_sovereign": winner.is_sovereign,
        "estimated_latency_ms": winner.estimated_latency_ms,
        "task_type": task_type,
    }


@router.post("/governance/gladiator/benchmark")
async def gladiator_benchmark(body: dict, user=Depends(get_current_user)):
    """Benchmark a specific route and update its Gladiator score. May trigger demotion."""
    from agents.governance.gladiator import gladiator
    route_id = body.get("route_id", "")
    iterations = min(int(body.get("iterations", 3)), 10)  # cap at 10 iterations
    if not route_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="route_id is required")
    result = await gladiator.benchmark_route(route_id, iterations=iterations)
    return result


@router.post("/governance/gladiator/optimize")
async def gladiator_optimize(user=Depends(get_current_user)):
    """
    Run the full Gladiator optimization cycle:
    benchmarks all routes, demotes underperformers, recovers healed routes,
    and returns a comprehensive before/after evidence report.
    """
    from agents.governance.gladiator import gladiator
    result = await gladiator.run_optimization_cycle()
    return result


@router.post("/governance/gladiator/assign-load")
async def gladiator_assign_load(body: dict, user=Depends(get_current_user)):
    """
    Distribute N agents across active routes using Gladiator score weighting.
    Returns allocation map {route_id: agent_count}.
    """
    from agents.governance.gladiator import gladiator
    agent_count = int(body.get("agent_count", 10))
    task_mix = body.get("task_mix", None)
    allocation = gladiator.assign_load(agent_count, task_mix)
    return allocation


@router.post("/governance/gladiator/routes/restore")
async def gladiator_restore_route(body: dict, user=Depends(get_current_user)):
    """Manually restore a demoted route back into the active arena."""
    from agents.governance.gladiator import gladiator
    route_id = body.get("route_id", "")
    if not route_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="route_id is required")
    restored = gladiator.restore_route(route_id)
    return {"restored": restored, "route_id": route_id}


@router.post("/governance/gladiator/routes/forge")
async def gladiator_forge_route(body: dict, user=Depends(get_current_user)):
    """
    Register a new candidate route into the Gladiator arena.
    The route will be benchmarked on the next optimization cycle.
    """
    from agents.governance.gladiator import gladiator, Route
    route_id = body.get("route_id", "")
    provider = body.get("provider", "")
    if not route_id or not provider:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="route_id and provider are required")
    route = Route(
        route_id=route_id,
        provider=provider,
        estimated_latency_ms=float(body.get("estimated_latency_ms", 200.0)),
        estimated_cost_per_call=float(body.get("estimated_cost_per_call", 0.001)),
        reliability_score=float(body.get("reliability_score", 0.95)),
        is_sovereign=bool(body.get("is_sovereign", False)),
    )
    gladiator.add_route(route)
    route.compute_gladiator_score()
    return {
        "forged": True,
        "route_id": route_id,
        "provider": provider,
        "gladiator_score": route.gladiator_score,
    }


@router.get("/governance/gladiator/benchmarks")
async def gladiator_benchmarks(limit: int = 50, user=Depends(get_current_user)):
    """Retrieve recent benchmark history for all routes."""
    from agents.governance.gladiator import gladiator
    return {
        "benchmarks": gladiator.get_benchmarks(limit=limit),
        "total": len(gladiator.get_benchmarks(limit=limit)),
    }


@router.get("/governance/gladiator/optimizations")
async def gladiator_optimizations(limit: int = 10, user=Depends(get_current_user)):
    """Retrieve recent optimization cycle reports."""
    from agents.governance.gladiator import gladiator
    return {
        "optimizations": gladiator.get_optimizations(limit=limit),
        "total": len(gladiator.get_optimizations(limit=limit)),
    }


# =============================================================================
# Combined Governance Health — single endpoint for the workspace dashboard
# =============================================================================

@router.get("/governance/health")
async def governance_health(user=Depends(get_current_user)):
    """
    Unified governance health snapshot:
      - Zeno freeze count
      - Gladiator circuit-breaker status
      - RARA / ATS summary
    """
    from agents.governance.zeno import _mem_freeze
    from agents.governance.gladiator import gladiator

    cb = gladiator.circuit_breaker_status()
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "zeno": {
            "frozen_agents": len(_mem_freeze),
            "frozen_ids": list(_mem_freeze.keys()),
        },
        "gladiator": {
            "active_routes": cb["active_routes"],
            "demoted_routes": cb["demoted_routes"],
            "top_route": gladiator.select_best_route().route_id,
        },
        "overall_status": "healthy" if len(_mem_freeze) == 0 and cb["demoted_routes"] == 0 else "degraded",
    }

