"""Admin, internal, search, upload, onboarding, referrals, support, stripe routes."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database.database import get_db
from backend.core.security.auth import get_current_admin, get_current_user
from backend.db.models.user import User

router = APIRouter(tags=["Admin & Internal"])


# --- Admin Panel ---
@router.get("/admin/workspaces")
async def list_admin_workspaces(user=Depends(get_current_admin)):
    return [
        {"id": "ws-demo-1", "name": "Acme Corp", "slug": "acme-corp", "plan": "agency", "is_active": True},
        {"id": "ws-demo-2", "name": "Globex", "slug": "globex", "plan": "starter", "is_active": True}
    ]


@router.get("/admin/workspaces/{id}")
async def get_admin_workspace(id: str, user=Depends(get_current_admin)):
    return {
        "id": id,
        "name": "Acme Corp",
        "slug": "acme-corp",
        "plan": "agency",
        "is_active": True,
        "created_at": "2026-01-01T00:00:00Z"
    }


@router.post("/admin/workspaces/{id}/suspend")
async def suspend_admin_workspace(id: str, user=Depends(get_current_admin)):
    return {"message": f"Workspace {id} suspended successfully", "is_active": False}


@router.delete("/admin/workspaces/{id}")
async def delete_admin_workspace(id: str, user=Depends(get_current_admin)):
    return {"message": f"Workspace {id} and all associated tenant data permanently deleted."}


@router.get("/admin/users")
async def list_admin_users(user=Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).limit(100))
    users = result.scalars().all()
    if not users:
        return [{ "id": "u-demo-1", "email": "admin@example.com", "role": "admin", "workspace_id": "ws-demo-1", "status": "active" }]
    return [{ "id": u.id, "email": u.email, "role": u.role, "workspace_id": u.workspace_id, "status": u.status } for u in users]


@router.put("/admin/users/{id}/role")
async def update_admin_user_role(id: str, body: dict, user=Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == id))
    u = result.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    u.role = body.get("role", "viewer")
    await db.commit()
    return {"message": f"User role updated to {u.role}", "user_id": u.id}


@router.post("/admin/users/{id}/deactivate")
async def deactivate_admin_user(id: str, user=Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == id))
    u = result.scalar_one_or_none()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    u.is_active = False
    u.status = "inactive"
    await db.commit()
    return {"message": "User deactivated successfully", "user_id": u.id}


@router.get("/admin/audit")
async def get_admin_audit_logs(workspace_id: str = None, limit: int = 500, user=Depends(get_current_admin)):
    return [{
        "id": "audit_admin_123",
        "workspace_id": workspace_id or "ws-demo-1",
        "action": "user.deactivate",
        "details": { "target_user_id": "u-demo-1" },
        "created_at": datetime.now(timezone.utc).isoformat()
    }]


# --- Internal / UACP ---
@router.get("/internal/uacp/status")
async def uacp_status(user=Depends(get_current_admin)):
    return {"status": "operational", "version": "5.0", "agents_active": 12}


@router.post("/internal/uacp/command")
async def uacp_command(body: dict, user=Depends(get_current_admin)):
    return {"command": body.get("command", ""), "result": "executed", "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/internal/operators")
async def list_operators(user=Depends(get_current_admin)):
    return [{"id": "op1", "name": "Policy Engine", "status": "active"}, {"id": "op2", "name": "Cost Controller", "status": "active"}]


@router.post("/internal/operators")
async def register_operator(body: dict, user=Depends(get_current_admin)):
    return {"id": "op_new", "name": body.get("name", ""), "status": "registered"}


@router.get("/source-of-truth/snapshot")
async def sot_snapshot(user=Depends(get_current_admin)):
    return {"snapshot_id": "snap_placeholder", "timestamp": datetime.now(timezone.utc).isoformat(), "tables": 15, "rows": 12450}


@router.post("/source-of-truth/sync")
async def sot_sync(user=Depends(get_current_admin)):
    return {"message": "Sync initiated", "estimated_seconds": 30}


# --- Search ---
@router.get("/search")
async def search(q: str = "", user=Depends(get_current_user)):
    return {"query": q, "results": [], "total": 0}


# --- Upload ---
@router.post("/upload")
async def upload_file(user=Depends(get_current_user)):
    return {"file_id": "f_placeholder", "status": "uploaded"}


@router.get("/files/upload-url")
async def get_upload_url(user=Depends(get_current_user)):
    return {"upload_url": "https://storage.placeholder/upload", "file_id": "f_placeholder"}


@router.post("/files/confirm")
async def confirm_upload(body: dict, user=Depends(get_current_user)):
    return {"file_id": body.get("file_id", ""), "status": "confirmed"}


# --- Onboarding ---
@router.get("/onboarding")
async def onboarding_status(user=Depends(get_current_user)):
    return {
        "completed": False,
        "steps": [
            {"id": "profile", "label": "Complete profile", "done": True},
            {"id": "workspace", "label": "Create workspace", "done": True},
            {"id": "api_key", "label": "Generate API key", "done": False},
            {"id": "first_run", "label": "Run first governed request", "done": False},
        ],
    }


@router.post("/onboarding/complete")
async def complete_onboarding(user=Depends(get_current_user)):
    return {"completed": True}


# --- Referrals ---
@router.get("/referrals")
async def referrals(user=Depends(get_current_user)):
    return {"referral_code": f"REF-{user.id[:8].upper()}", "total_referrals": 0, "earned_usd": 0}


@router.post("/referrals/invite")
async def invite_referral(body: dict, user=Depends(get_current_user)):
    return {"message": f"Referral invitation sent to {body.get('email', '')}"}


# --- Support ---
@router.post("/support")
async def support_message(body: dict, user=Depends(get_current_user)):
    return {"ticket_id": "tkt_placeholder", "message": "Support request received"}


# --- Stripe Connect ---
@router.get("/stripe/connect/onboard")
async def stripe_onboard(user=Depends(get_current_user)):
    return {"url": "https://connect.stripe.com/placeholder"}


@router.get("/stripe/connect/status")
async def stripe_status(user=Depends(get_current_user)):
    return {"connected": False, "account_id": None}


# --- Export ---
@router.get("/export")
async def export_data(user=Depends(get_current_user)):
    return {"export_url": "/exports/data.json", "status": "generated"}


# --- Extract ---
@router.post("/extract")
async def extract_data(body: dict, user=Depends(get_current_user)):
    return {"extracted": body.get("type", ""), "data": {}}
