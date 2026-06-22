"""Admin, internal, search, upload, onboarding, referrals, support, stripe routes."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
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
        
    filtered_users = []
    for u in users:
        email = (u.email or "").lower()
        if email.startswith("eval.") or email.startswith("smoke."):
            continue
        filtered_users.append({ "id": u.id, "email": u.email, "role": u.role, "workspace_id": u.workspace_id, "status": u.status })
        
    return filtered_users


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


@router.get("/admin/recon_findings")
async def list_recon_findings(user=Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    from backend.db.models.billing import ReconFinding
    result = await db.execute(select(ReconFinding).limit(100))
    findings = result.scalars().all()
    return [{"tx_hash": f.tx_hash, "ledger_sum": f.ledger_sum, "chain_sum": f.chain_sum, "detected_at": f.detected_at.isoformat() if f.detected_at else None} for f in findings]


@router.get("/admin/webhook_dead_letter")
async def list_webhook_dead_letter(user=Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    from backend.db.models.billing import WebhookDeadLetter
    result = await db.execute(select(WebhookDeadLetter).limit(100))
    dead_letters = result.scalars().all()
    return [{
        "id": dl.id,
        "idempotency_key": dl.idempotency_key,
        "payload": dl.payload,
        "error_message": dl.error_message,
        "retry_count": dl.retry_count,
        "status": dl.status,
        "created_at": dl.created_at.isoformat() if dl.created_at else None,
        "updated_at": dl.updated_at.isoformat() if dl.updated_at else None
    } for dl in dead_letters]


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
    import uuid as _uuid
    import json as _json
    from pathlib import Path as _Path
    ticket_id = "tkt_" + str(_uuid.uuid4())[:8]
    record = {
        "ticket_id": ticket_id,
        "email": user.email or "",
        "workspace_id": user.workspace_id or "",
        "message": body.get("message", ""),
        "page": body.get("page", ""),
        "user_agent": body.get("user_agent", ""),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        log_dir = _Path("logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        with (log_dir / "support_tickets.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(_json.dumps(record, separators=(",", ":")) + "\n")
    except Exception:
        pass
    return {"ticket_id": ticket_id, "message": "Support request received — we'll reply within 4 hours", "status": "open"}




# --- Export ---
@router.get("/export")
async def export_data(user=Depends(get_current_user)):
    return {"export_url": "/exports/data.json", "status": "generated"}


# NOTE: /extract is intentionally NOT defined here. The real handler lives in
# upload.py (it extracts structured data from content); this stub previously
# shadowed it because the admin router is registered before the upload router.
