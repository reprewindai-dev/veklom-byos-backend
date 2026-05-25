"""Command Center routes — /api/v1/command-center/*.

Implements the namespace required by docs/WIRING_MATRIX.md.

Group A (aliases):  thin pass-throughs to existing handlers.  No data is
                    duplicated; each alias either calls the underlying
                    handler or runs the same query so frontend pages that
                    expect /command-center/* paths can talk to real data.

Group B (new):      first-class routes for funnels, online users, recent
                    users, summary, sessions, errors, terminals map.
                    Backed by real DB queries on existing tables; no fake
                    data.  Where a metric cannot be computed (e.g. error
                    feed which lives in Sentry), the endpoint returns
                    {"available": false, "reason": "..."} so the UI can
                    render an explicit "Unavailable" state instead of a
                    fabricated number.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database.database import get_db
from backend.core.security.auth import get_current_user
from backend.db.models.security import AuditLog, SecurityEvent
from backend.db.models.user import Session as UserSession
from backend.db.models.user import User
from backend.db.models.workspace import Workspace

router = APIRouter(prefix="/command-center", tags=["Command Center"])


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _require_platform_superuser(user) -> None:
    """Require platform superuser access - NOT tenant owner access.
    
    Platform superuser is defined as:
    - user.is_superuser is true
    - OR user.role == SUPER_ADMIN
    - OR user.email == settings.ADMIN_EMAIL
    - OR user.workspace_id == settings.FOUNDER_WORKSPACE_ID
    
    Tenant OWNER role does NOT grant platform superuser access.
    """
    from backend.core.config.settings import settings
    
    is_superuser = bool(getattr(user, "is_superuser", False))
    role = (getattr(user, "role", "") or "").upper()
    email = getattr(user, "email", "")
    workspace_id = getattr(user, "workspace_id", "")
    
    # Check if user is platform superuser
    is_platform_superuser = (
        is_superuser
        or role == "SUPER_ADMIN"
        or email == settings.ADMIN_EMAIL
        or workspace_id == settings.FOUNDER_WORKSPACE_ID
    )
    
    if not is_platform_superuser:
        raise HTTPException(status_code=403, detail="Command Center is platform-superuser only")


def _safe_user(u: User) -> dict:
    """Strip every secret-bearing field before returning a user."""
    return {
        "id": u.id,
        "email": u.email,
        "full_name": u.full_name or "",
        "role": u.role,
        "status": u.status,
        "is_active": u.is_active,
        "workspace_id": u.workspace_id,
        "github_username": u.github_username,
        "mfa_enabled": bool(u.mfa_enabled),
        "last_login": u.last_login.isoformat() if u.last_login else None,
        "last_activity": u.last_activity.isoformat() if u.last_activity else None,
        "created_at": u.created_at.isoformat() if u.created_at else None,
    }


# ---------------------------------------------------------------------------
# Group A — Aliases to existing handlers
# ---------------------------------------------------------------------------

@router.get("/overview")
async def overview(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Workspace-scoped overview: totals, last activity, headline metrics.

    Aliases /api/v1/workspace/overview semantics but always returns concrete
    counts pulled from the DB.  No fake fallbacks.
    """
    ws = user.workspace_id or ""
    total_users = (await db.execute(
        select(func.count(User.id)).where(User.workspace_id == ws)
    )).scalar() or 0
    active_users = (await db.execute(
        select(func.count(User.id)).where(
            User.workspace_id == ws, User.is_active == True  # noqa: E712
        )
    )).scalar() or 0
    audit_24h = (await db.execute(
        select(func.count(AuditLog.id)).where(
            AuditLog.workspace_id == ws,
            AuditLog.created_at >= _utcnow() - timedelta(hours=24),
        )
    )).scalar() or 0
    open_security = (await db.execute(
        select(func.count(SecurityEvent.id)).where(
            SecurityEvent.workspace_id == ws, SecurityEvent.status == "open"
        )
    )).scalar() or 0
    return {
        "workspace_id": ws,
        "as_of": _utcnow().isoformat(),
        "users_total": total_users,
        "users_active": active_users,
        "audit_events_24h": audit_24h,
        "open_security_events": open_security,
    }


@router.get("/audit-log")
async def audit_log(
    limit: int = Query(50, ge=1, le=500),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ws = user.workspace_id or ""
    rows = (await db.execute(
        select(AuditLog)
        .where(AuditLog.workspace_id == ws)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
    )).scalars().all()
    return [
        {
            "id": r.id,
            "user_id": r.user_id,
            "workspace_id": r.workspace_id,
            "action": r.action,
            "resource_type": r.resource_type,
            "resource_id": r.resource_id,
            "details": r.details,
            "hash_chain": r.hash_chain,
            "prev_hash": r.prev_hash,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.get("/users")
async def users_list(
    limit: int = Query(100, ge=1, le=500),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Workspace-scoped user list. Admin-only."""
    _require_platform_superuser(user)
    ws = user.workspace_id or ""
    rows = (await db.execute(
        select(User).where(User.workspace_id == ws).limit(limit)
    )).scalars().all()
    return [_safe_user(u) for u in rows]


@router.get("/users/{user_id}")
async def user_detail(
    user_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_platform_superuser(user)
    ws = user.workspace_id or ""
    u = (await db.execute(
        select(User).where(User.id == user_id, User.workspace_id == ws)
    )).scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    return _safe_user(u)


@router.get("/users/{user_id}/activity")
async def user_activity(
    user_id: str,
    limit: int = Query(50, ge=1, le=500),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_platform_superuser(user)
    ws = user.workspace_id or ""
    rows = (await db.execute(
        select(AuditLog)
        .where(AuditLog.workspace_id == ws, AuditLog.user_id == user_id)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
    )).scalars().all()
    return [
        {
            "id": r.id,
            "action": r.action,
            "resource_type": r.resource_type,
            "resource_id": r.resource_id,
            "details": r.details,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.get("/users/{user_id}/sessions")
async def user_sessions(
    user_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_platform_superuser(user)
    ws = user.workspace_id or ""
    target = (await db.execute(
        select(User).where(User.id == user_id, User.workspace_id == ws)
    )).scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    rows = (await db.execute(
        select(UserSession)
        .where(UserSession.user_id == user_id)
        .order_by(UserSession.last_accessed.desc())
    )).scalars().all()
    return [
        {
            "id": s.id,
            "user_id": s.user_id,
            "ip_address": s.ip_address,
            "user_agent": s.user_agent,
            "is_active": s.is_active,
            "expires_at": s.expires_at.isoformat() if s.expires_at else None,
            "last_accessed": s.last_accessed.isoformat() if s.last_accessed else None,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in rows
    ]


@router.get("/operations/health")
async def operations_health(user=Depends(get_current_user)):
    """Alias for /api/v1/monitoring/health."""
    from backend.apps.api.routers.monitoring import monitoring_health
    return await monitoring_health(user=user)


@router.get("/operations/alerts")
async def operations_alerts(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ws = user.workspace_id or ""
    rows = (await db.execute(
        select(SecurityEvent)
        .where(SecurityEvent.workspace_id == ws, SecurityEvent.status == "open")
        .order_by(SecurityEvent.created_at.desc())
        .limit(100)
    )).scalars().all()
    return [
        {
            "id": e.id,
            "event_type": e.event_type,
            "severity": e.severity,
            "description": e.description,
            "status": e.status,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in rows
    ]


@router.get("/operations/errors")
async def operations_errors():
    """Errors live in Sentry, not in our DB.  Be honest about it."""
    return {
        "available": False,
        "reason": "Error feed is captured in Sentry. No local error store.",
        "sentry_org": "veklom-sovereign-ai-hub-p0",
        "sentry_project": "lockerphycer",
    }


@router.get("/business/billing")
async def business_billing(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Alias for /api/v1/workspace/billing/breakdown."""
    from backend.apps.api.routers.workspace import billing_breakdown as ws_bb
    return await ws_bb(user=user, db=db)


@router.get("/activity-feed")
async def activity_feed(
    limit: int = Query(50, ge=1, le=200),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Combined recent activity: audit log + security events."""
    ws = user.workspace_id or ""
    cutoff = _utcnow() - timedelta(hours=72)
    audit = (await db.execute(
        select(AuditLog)
        .where(AuditLog.workspace_id == ws, AuditLog.created_at >= cutoff)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
    )).scalars().all()
    sec = (await db.execute(
        select(SecurityEvent)
        .where(SecurityEvent.workspace_id == ws, SecurityEvent.created_at >= cutoff)
        .order_by(SecurityEvent.created_at.desc())
        .limit(limit)
    )).scalars().all()
    feed = []
    for a in audit:
        feed.append({
            "kind": "audit",
            "id": a.id,
            "user_id": a.user_id,
            "action": a.action,
            "resource_type": a.resource_type,
            "resource_id": a.resource_id,
            "timestamp": a.created_at.isoformat() if a.created_at else None,
        })
    for s in sec:
        feed.append({
            "kind": "security",
            "id": s.id,
            "user_id": s.user_id,
            "action": s.event_type,
            "severity": s.severity,
            "description": s.description,
            "timestamp": s.created_at.isoformat() if s.created_at else None,
        })
    feed.sort(key=lambda r: r.get("timestamp") or "", reverse=True)
    return feed[:limit]


# ---------------------------------------------------------------------------
# Group B — New routes
# ---------------------------------------------------------------------------

@router.get("/users/summary")
async def users_summary(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_platform_superuser(user)
    ws = user.workspace_id or ""
    total = (await db.execute(
        select(func.count(User.id)).where(User.workspace_id == ws)
    )).scalar() or 0
    active = (await db.execute(
        select(func.count(User.id)).where(
            User.workspace_id == ws, User.is_active == True  # noqa: E712
        )
    )).scalar() or 0
    locked = (await db.execute(
        select(func.count(User.id)).where(
            User.workspace_id == ws, User.status == "LOCKED"
        )
    )).scalar() or 0
    mfa_on = (await db.execute(
        select(func.count(User.id)).where(
            User.workspace_id == ws, User.mfa_enabled == True  # noqa: E712
        )
    )).scalar() or 0
    return {
        "workspace_id": ws,
        "total": total,
        "active": active,
        "locked": locked,
        "mfa_enabled": mfa_on,
    }


@router.get("/users/online")
async def users_online(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Online = has an active session whose expiry is in the future."""
    _require_platform_superuser(user)
    ws = user.workspace_id or ""
    now = _utcnow()
    rows = (await db.execute(
        select(User, UserSession)
        .join(UserSession, UserSession.user_id == User.id)
        .where(
            User.workspace_id == ws,
            UserSession.is_active == True,  # noqa: E712
            UserSession.expires_at > now,
        )
        .order_by(UserSession.last_accessed.desc())
    )).all()
    seen: dict[str, dict] = {}
    for u, s in rows:
        if u.id in seen:
            continue
        seen[u.id] = {
            **_safe_user(u),
            "session_id": s.id,
            "session_last_accessed": s.last_accessed.isoformat() if s.last_accessed else None,
        }
    return list(seen.values())


@router.get("/users/recent")
async def users_recent(
    days: int = Query(7, ge=1, le=90),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_platform_superuser(user)
    ws = user.workspace_id or ""
    cutoff = _utcnow() - timedelta(days=days)
    rows = (await db.execute(
        select(User)
        .where(User.workspace_id == ws, User.created_at >= cutoff)
        .order_by(User.created_at.desc())
        .limit(200)
    )).scalars().all()
    return [_safe_user(u) for u in rows]


@router.get("/live-users")
async def live_users(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Identical semantics to /users/online — provided so legacy callers using
    the spec'd path also work."""
    return await users_online(user=user, db=db)


@router.get("/sessions")
async def sessions_list(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Active sessions across the workspace.  Admin-only. Tokens stripped."""
    _require_platform_superuser(user)
    ws = user.workspace_id or ""
    now = _utcnow()
    rows = (await db.execute(
        select(UserSession, User)
        .join(User, User.id == UserSession.user_id)
        .where(
            User.workspace_id == ws,
            UserSession.is_active == True,  # noqa: E712
            UserSession.expires_at > now,
        )
        .order_by(UserSession.last_accessed.desc())
        .limit(500)
    )).all()
    return [
        {
            "id": s.id,
            "user_id": s.user_id,
            "user_email": u.email,
            "ip_address": s.ip_address,
            "user_agent": s.user_agent,
            "expires_at": s.expires_at.isoformat() if s.expires_at else None,
            "last_accessed": s.last_accessed.isoformat() if s.last_accessed else None,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s, u in rows
    ]


@router.get("/funnels")
async def funnels(
    days: int = Query(30, ge=1, le=365),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Signup → activation → first-key → first-install funnel for the workspace."""
    _require_platform_superuser(user)
    ws = user.workspace_id or ""
    cutoff = _utcnow() - timedelta(days=days)
    signups = (await db.execute(
        select(func.count(User.id)).where(
            User.workspace_id == ws, User.created_at >= cutoff
        )
    )).scalar() or 0
    activated = (await db.execute(
        select(func.count(User.id)).where(
            User.workspace_id == ws,
            User.created_at >= cutoff,
            User.last_login.isnot(None),
        )
    )).scalar() or 0
    # Approximate "first install" via marketplace install audit events.
    installs = (await db.execute(
        select(func.count(AuditLog.id)).where(
            AuditLog.workspace_id == ws,
            AuditLog.created_at >= cutoff,
            AuditLog.action.in_(("marketplace.install", "listing.installed")),
        )
    )).scalar() or 0
    return {
        "window_days": days,
        "as_of": _utcnow().isoformat(),
        "signups": signups,
        "activated": activated,
        "installs": installs,
        "activation_rate": (activated / signups) if signups else 0.0,
        "install_rate": (installs / activated) if activated else 0.0,
    }


@router.get("/terminals/quantum")
async def terminals_quantum(user=Depends(get_current_user)):
    """UACP / Quantum terminal endpoint map.

    Returns the documented allowlist of backend routes a terminal command can
    dispatch to.  The terminal frontend MUST refuse any command not present in
    this map.  No command is executed by this endpoint itself.
    """
    return {
        "name": "UACP Quantum Terminal",
        "version": "1.0",
        "auth_required": True,
        "endpoints": [
            {"label": "ping", "method": "GET", "path": "/health"},
            {"label": "uacp.summary", "method": "GET", "path": "/api/v1/internal/uacp/summary"},
            {"label": "uacp.events", "method": "GET", "path": "/api/v1/internal/uacp/events"},
            {"label": "uacp.runs", "method": "GET", "path": "/api/v1/internal/uacp/runs"},
            {"label": "uacp.evidence", "method": "GET", "path": "/api/v1/internal/uacp/evidence"},
            {"label": "uacp.monitoring", "method": "GET", "path": "/api/v1/internal/uacp/monitoring"},
            {"label": "uacp.security", "method": "GET", "path": "/api/v1/internal/uacp/security"},
            {"label": "uacp.versions", "method": "GET", "path": "/api/v1/internal/uacp/versions"},
            {"label": "uacp.workspaces", "method": "GET", "path": "/api/v1/internal/uacp/workspaces"},
            {"label": "uacp.dispatch.v4", "method": "POST", "path": "/api/v1/internal/uacp/v4/dispatch"},
        ],
    }


@router.get("/terminals/veklom")
async def terminals_veklom(user=Depends(get_current_user)):
    """Veklom Runtime terminal endpoint map."""
    return {
        "name": "Veklom Runtime Terminal",
        "version": "1.0",
        "auth_required": True,
        "endpoints": [
            {"label": "health", "method": "GET", "path": "/health"},
            {"label": "health.detailed", "method": "GET", "path": "/health/detailed"},
            {"label": "platform.pulse", "method": "GET", "path": "/api/v1/platform/pulse"},
            {"label": "platform.uptime", "method": "GET", "path": "/api/v1/platform/uptime"},
            {"label": "monitoring.dashboard", "method": "GET", "path": "/api/v1/monitoring/dashboard"},
            {"label": "monitoring.metrics", "method": "GET", "path": "/api/v1/monitoring/metrics"},
            {"label": "monitoring.events", "method": "GET", "path": "/api/v1/monitoring/events"},
            {"label": "gpc.bootstrap", "method": "GET", "path": "/api/v1/gpc/bootstrap"},
            {"label": "gpc.runs", "method": "GET", "path": "/api/v1/gpc/runs"},
            {"label": "gpc.events", "method": "GET", "path": "/api/v1/gpc/events"},
            {"label": "audit.logs", "method": "GET", "path": "/api/v1/audit/logs"},
            {"label": "deployments.list", "method": "GET", "path": "/api/v1/deployments"},
            {"label": "kill_switch.status", "method": "GET", "path": "/api/v1/kill-switch/status"},
        ],
    }
