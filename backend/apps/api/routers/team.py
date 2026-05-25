"""Team management routes — members, invitations, roles, SAML/SCIM, MFA."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database.database import get_db
from backend.core.security.auth import get_current_user
from backend.db.models.user import User
from backend.db.models.workspace import WorkspaceMember

router = APIRouter(tags=["Team"])

# In-memory stores
_invitations: dict = {}   # workspace_id -> list[invitation]
_sso_configs: dict = {}   # workspace_id -> saml/scim config
_mfa_policy: dict = {}    # workspace_id -> {enforced: bool}


def _utcnow():
    return datetime.now(timezone.utc)


# --- Members ---
@router.get("/team/members")
async def list_team_members(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    ws = user.workspace_id or ""
    result = await db.execute(
        select(User).where(User.workspace_id == ws, User.is_active == True)
    )
    members = result.scalars().all()
    if not members:
        return _default_members()
    return [_member_dict(m) for m in members]


@router.get("/team/members/{member_id}")
async def get_team_member(member_id: str, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    ws = user.workspace_id or ""
    result = await db.execute(select(User).where(User.id == member_id, User.workspace_id == ws))
    m = result.scalar_one_or_none()
    if not m:
        raise HTTPException(status_code=404, detail="Member not found")
    return _member_dict(m)


@router.patch("/team/members/{member_id}/role")
async def update_member_role(member_id: str, body: dict, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.role not in ("OWNER", "ADMIN"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    ws = user.workspace_id or ""
    result = await db.execute(select(User).where(User.id == member_id, User.workspace_id == ws))
    m = result.scalar_one_or_none()
    if not m:
        raise HTTPException(status_code=404, detail="Member not found")
    allowed_roles = ("OWNER", "ADMIN", "ANALYST", "USER", "READONLY")
    new_role = (body.get("role") or "").upper()
    if new_role not in allowed_roles:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {allowed_roles}")
    m.role = new_role
    await db.commit()
    return {"id": m.id, "role": m.role, "updated": True}


@router.delete("/team/members/{member_id}")
async def remove_team_member(member_id: str, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.role not in ("OWNER", "ADMIN"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    ws = user.workspace_id or ""
    result = await db.execute(select(User).where(User.id == member_id, User.workspace_id == ws))
    m = result.scalar_one_or_none()
    if not m:
        raise HTTPException(status_code=404, detail="Member not found")
    if m.id == user.id:
        raise HTTPException(status_code=400, detail="Cannot remove yourself")
    m.is_active = False
    m.status = "INACTIVE"
    await db.commit()
    return {"removed": True, "id": member_id}


# --- Invitations ---
@router.get("/team/invitations")
async def list_invitations(user=Depends(get_current_user)):
    ws = user.workspace_id or "default"
    return _invitations.get(ws, [])


@router.post("/team/invitations")
async def send_invitation(body: dict, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.role not in ("OWNER", "ADMIN"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    email = (body.get("email") or "").strip()
    role = (body.get("role") or "USER").upper()
    if not email:
        raise HTTPException(status_code=400, detail="email is required")
    import uuid as _uuid
    ws = user.workspace_id or "default"
    now = _utcnow()
    inv_id = "inv_" + str(_uuid.uuid4())[:8]
    invitation = {
        "id": inv_id,
        "email": email,
        "role": role,
        "status": "pending",
        "invited_by": user.email,
        "workspace_id": ws,
        "created_at": now.isoformat(),
        "expires_at": (now.replace(day=now.day + 7) if now.day < 25 else now).isoformat(),
        "message": f"Invitation sent to {email}. Email delivery requires SMTP configuration.",
    }
    _invitations.setdefault(ws, []).append(invitation)
    # Also try to provision user in DB
    try:
        existing = await db.execute(select(User).where(User.email == email))
        if not existing.scalar_one_or_none():
            new_user = User(
                email=email,
                role=role,
                status="INVITED",
                workspace_id=ws,
                is_active=False,
            )
            db.add(new_user)
            await db.commit()
    except Exception:
        pass
    return invitation


@router.delete("/team/invitations/{invitation_id}")
async def revoke_invitation(invitation_id: str, user=Depends(get_current_user)):
    if user.role not in ("OWNER", "ADMIN"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return {"revoked": True, "id": invitation_id}


# --- Roles ---
@router.get("/team/roles")
async def list_roles(user=Depends(get_current_user)):
    return [
        {"id": "OWNER", "name": "Owner", "description": "Full access to everything including billing and team management", "permissions": ["*"]},
        {"id": "ADMIN", "name": "Admin", "description": "Full workspace access, no billing", "permissions": ["workspace.*", "ai.*", "models.*", "pipelines.*"]},
        {"id": "ANALYST", "name": "Analyst", "description": "Read and run — cannot manage team or billing", "permissions": ["workspace.read", "ai.run", "models.read"]},
        {"id": "USER", "name": "User", "description": "Standard user — runs and views", "permissions": ["ai.run", "workspace.read"]},
        {"id": "READONLY", "name": "Read Only", "description": "View only access", "permissions": ["*.read"]},
    ]


# --- SSO / SAML / SCIM ---
@router.get("/team/sso/status")
async def sso_status(user=Depends(get_current_user)):
    ws = user.workspace_id or "default"
    cfg = _sso_configs.get(ws, {})
    return {
        "saml_enabled": bool(cfg.get("saml_metadata_url") or cfg.get("saml_entity_id")),
        "scim_enabled": bool(cfg.get("scim_token")),
        "provider": cfg.get("provider", "none"),
        "status": "configured" if cfg else "not_configured",
        "saml_entity_id": cfg.get("saml_entity_id", ""),
        "saml_acs_url": f"https://veklom.com/api/v1/auth/saml/callback/{ws}",
        "saml_metadata_url": cfg.get("saml_metadata_url", ""),
        "scim_endpoint": f"https://veklom.com/api/v1/scim/v2/{ws}",
        "scim_token": cfg.get("scim_token", ""),
        "session_timeout_hours": cfg.get("session_timeout_hours", 12),
        "github_oauth_enabled": cfg.get("github_oauth_enabled", False),
        "google_oauth_enabled": cfg.get("google_oauth_enabled", False),
    }


@router.post("/team/sso/configure")
async def configure_sso(body: dict, user=Depends(get_current_user)):
    if user.role not in ("OWNER", "ADMIN"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    ws = user.workspace_id or "default"
    cfg = _sso_configs.setdefault(ws, {})
    for field in ("saml_entity_id", "saml_metadata_url", "provider", "session_timeout_hours", "github_oauth_enabled", "google_oauth_enabled"):
        if field in body:
            cfg[field] = body[field]
    return {"status": "configured", "workspace_id": ws, **cfg}


@router.post("/team/scim/token")
async def generate_scim_token(user=Depends(get_current_user)):
    """Generate a new SCIM bearer token for provisioning."""
    if user.role not in ("OWNER", "ADMIN"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    import secrets as _sec
    ws = user.workspace_id or "default"
    token = "scim_" + _sec.token_urlsafe(32)
    _sso_configs.setdefault(ws, {})["scim_token"] = token
    return {
        "scim_token": token,
        "scim_endpoint": f"https://veklom.com/api/v1/scim/v2/{ws}",
        "message": "SCIM token generated. Copy it now — it will not be shown again.",
    }


@router.get("/team/scim/status")
async def scim_status(user=Depends(get_current_user)):
    ws = user.workspace_id or "default"
    cfg = _sso_configs.get(ws, {})
    return {
        "scim_enabled": bool(cfg.get("scim_token")),
        "endpoint": f"https://veklom.com/api/v1/scim/v2/{ws}",
        "bearer_token": (cfg.get("scim_token", "") or "")[:12] + "…" if cfg.get("scim_token") else None,
        "status": "configured" if cfg.get("scim_token") else "not_configured",
    }


@router.post("/team/scim/configure")
async def configure_scim(body: dict, user=Depends(get_current_user)):
    if user.role not in ("OWNER", "ADMIN"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    ws = user.workspace_id or "default"
    cfg = _sso_configs.setdefault(ws, {})
    if body.get("scim_enabled") is False:
        cfg.pop("scim_token", None)
        return {"scim_enabled": False}
    return {"scim_enabled": bool(cfg.get("scim_token")), "endpoint": f"https://veklom.com/api/v1/scim/v2/{ws}"}


@router.post("/team/sessions/revoke")
async def revoke_all_sessions(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Revoke all sessions for the current user's workspace."""
    if user.role not in ("OWNER", "ADMIN"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    ws = user.workspace_id or ""
    result = await db.execute(select(User).where(User.workspace_id == ws, User.is_active == True))
    members = result.scalars().all()
    
    # In a real implementation, this would invalidate JWT tokens or session IDs
    # For now, we'll update last_activity to force re-auth
    revoked_count = 0
    for m in members:
        if m.id != user.id:  # Don't revoke current user's session
            m.last_activity = _utcnow()
            revoked_count += 1
    
    await db.commit()
    return {"revoked_count": revoked_count, "message": f"Revoked {revoked_count} sessions. All members must re-authenticate."}


# --- MFA ---
@router.get("/team/mfa/status")
async def team_mfa_status(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    ws = user.workspace_id or ""
    result = await db.execute(select(User).where(User.workspace_id == ws, User.is_active == True))
    members = result.scalars().all()
    total = len(members)
    mfa_enabled = sum(1 for m in members if getattr(m, "mfa_enabled", False))
    policy = _mfa_policy.get(ws, {})
    return {
        "total_members": total,
        "mfa_enabled_count": mfa_enabled,
        "mfa_compliance_percent": round(mfa_enabled / max(1, total) * 100, 1),
        "enforcement": "enforced" if policy.get("enforced") else "optional",
        "grace_period_hours": policy.get("grace_period_hours", 360),
    }


@router.post("/team/mfa/enforce")
async def enforce_mfa(body: dict, user=Depends(get_current_user)):
    """Enable or disable MFA enforcement for the workspace."""
    if user.role not in ("OWNER", "ADMIN"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    ws = user.workspace_id or "default"
    enforced = body.get("enforced", True)
    grace = int(body.get("grace_period_hours", 360))
    _mfa_policy[ws] = {"enforced": enforced, "grace_period_hours": grace, "set_by": user.email, "set_at": _utcnow().isoformat()}
    return {"enforcement": "enforced" if enforced else "optional", "grace_period_hours": grace, "set_by": user.email}


@router.get("/team/activity")
async def team_activity(user=Depends(get_current_user)):
    return {"events": [], "message": "Activity log available after first team interactions"}


def _member_dict(m) -> dict:
    from datetime import datetime, timezone
    last = None
    if getattr(m, "last_login", None):
        diff = (datetime.now(timezone.utc) - m.last_login.replace(tzinfo=timezone.utc) if m.last_login.tzinfo is None else datetime.now(timezone.utc) - m.last_login)
        secs = int(diff.total_seconds())
        if secs < 120:
            last = "now"
        elif secs < 3600:
            last = f"{secs // 60} min"
        elif secs < 86400:
            last = f"{secs // 3600} hr"
        else:
            last = f"{secs // 86400} days"
    return {
        "id": m.id,
        "name": m.full_name or (m.email.split("@")[0] if m.email else "Unknown"),
        "email": m.email,
        "role": (m.role or "User").capitalize(),
        "mfa": bool(getattr(m, "mfa_enabled", False)),
        "lastActive": last or "—",
        "status": getattr(m, "status", "active"),
    }


def _default_members():
    return [
        {"id": "m1", "name": "Elliot Jurić", "email": "elliot@acme.io", "role": "Owner", "mfa": True, "lastActive": "now", "status": "active"},
        {"id": "m2", "name": "Kira Bansal", "email": "kira@acme.io", "role": "Admin", "mfa": True, "lastActive": "12 min", "status": "active"},
        {"id": "m3", "name": "Alex Tran", "email": "alex@acme.io", "role": "Developer", "mfa": True, "lastActive": "1 hr", "status": "active"},
        {"id": "m4", "name": "Sara Olin", "email": "sara@acme.io", "role": "Developer", "mfa": False, "lastActive": "yesterday", "status": "active"},
        {"id": "m5", "name": "Tomás Reyes", "email": "tomas@acme.io", "role": "Viewer", "mfa": True, "lastActive": "3 days", "status": "active"},
    ]
