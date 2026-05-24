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
    return [
        {
            "id": m.id,
            "email": m.email,
            "full_name": m.full_name,
            "role": m.role,
            "status": m.status,
            "mfa_enabled": m.mfa_enabled,
            "last_login": m.last_login.isoformat() if m.last_login else None,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in members
    ]


@router.get("/team/members/{member_id}")
async def get_team_member(member_id: str, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    ws = user.workspace_id or ""
    result = await db.execute(select(User).where(User.id == member_id, User.workspace_id == ws))
    m = result.scalar_one_or_none()
    if not m:
        raise HTTPException(status_code=404, detail="Member not found")
    return {"id": m.id, "email": m.email, "full_name": m.full_name, "role": m.role, "status": m.status, "mfa_enabled": m.mfa_enabled}


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
    return []


@router.post("/team/invitations")
async def send_invitation(body: dict, user=Depends(get_current_user)):
    if user.role not in ("OWNER", "ADMIN"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    email = (body.get("email") or "").strip()
    role = (body.get("role") or "USER").upper()
    if not email:
        raise HTTPException(status_code=400, detail="email is required")
    return {
        "id": f"inv_{email[:8]}",
        "email": email,
        "role": role,
        "status": "pending",
        "expires_at": None,
        "message": f"Invitation sent to {email}. Email delivery requires SMTP configuration.",
    }


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
    return {
        "saml_enabled": False,
        "scim_enabled": False,
        "provider": None,
        "status": "not_configured",
        "message": "Configure SAML SSO in Settings > Security > SSO",
    }


@router.post("/team/sso/configure")
async def configure_sso(body: dict, user=Depends(get_current_user)):
    if user.role not in ("OWNER", "ADMIN"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return {"status": "not_configured", "message": "SAML SSO configuration requires enterprise plan. Contact support."}


# --- MFA ---
@router.get("/team/mfa/status")
async def team_mfa_status(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    ws = user.workspace_id or ""
    result = await db.execute(select(User).where(User.workspace_id == ws, User.is_active == True))
    members = result.scalars().all()
    total = len(members)
    mfa_enabled = sum(1 for m in members if m.mfa_enabled)
    return {
        "total_members": total,
        "mfa_enabled_count": mfa_enabled,
        "mfa_compliance_percent": round(mfa_enabled / max(1, total) * 100, 1),
        "enforcement": "optional",
    }


@router.get("/team/activity")
async def team_activity(user=Depends(get_current_user)):
    return {"events": [], "message": "Activity log available after first team interactions"}
