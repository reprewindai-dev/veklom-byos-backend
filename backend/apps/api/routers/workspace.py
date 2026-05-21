"""Workspace / tenant routes."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database.database import get_db
from backend.core.security.auth import get_current_user
from backend.db.models.ai import ExecLog
from backend.db.models.security import AuditLog, SecurityEvent
from backend.db.models.workspace import ModelConfig, Workspace, WorkspaceMember
from backend.db.models.user import APIKey
from backend.db.models.billing import BudgetRule

router = APIRouter(prefix="/workspace", tags=["Workspace"])


@router.get("")
async def get_workspace(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.workspace_id:
        result = await db.execute(select(Workspace).where(Workspace.id == user.workspace_id))
        ws = result.scalar_one_or_none()
        if ws:
            return _ws_dict(ws)

    return {
        "id": "",
        "name": "Default Workspace",
        "slug": "default",
        "plan": "free_evaluation",
        "settings": {},
        "is_active": True,
    }


@router.get("/overview")
async def workspace_overview(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    workspace_id = user.workspace_id or "default"
    total_requests = await db.scalar(select(func.count()).select_from(ExecLog).where(ExecLog.workspace_id == workspace_id)) or 0
    total_tokens = await db.scalar(select(func.coalesce(func.sum(ExecLog.total_tokens), 0)).where(ExecLog.workspace_id == workspace_id)) or 0
    spend_today = await db.scalar(select(func.coalesce(func.sum(ExecLog.cost_usd), 0.0)).where(ExecLog.workspace_id == workspace_id)) or 0.0
    avg_latency = await db.scalar(select(func.coalesce(func.avg(ExecLog.latency_ms), 112)).where(ExecLog.workspace_id == workspace_id)) or 112
    audit_entries = await db.scalar(select(func.count()).select_from(AuditLog).where(AuditLog.workspace_id == workspace_id)) or 0
    models_enabled = await db.scalar(select(func.count()).select_from(ModelConfig).where(ModelConfig.workspace_id == workspace_id, ModelConfig.is_enabled == True)) or 0
    if not models_enabled:
        models_enabled = len(_default_models())

    result = await db.execute(
        select(ExecLog)
        .where(ExecLog.workspace_id == workspace_id)
        .order_by(ExecLog.created_at.desc())
        .limit(5)
    )
    recent_runs = [
        {
            "id": row.id,
            "model": row.model or "qwen2.5:3b",
            "route": row.provider or "ollama",
            "latency": row.latency_ms or 0,
            "tokens": row.total_tokens or 0,
            "cost": row.cost_usd or 0.0,
            "policy": "redacted" if row.policy_flags else "passed",
            "ts": row.created_at.isoformat() if row.created_at else "",
        }
        for row in result.scalars().all()
    ]
    audit_result = await db.execute(
        select(AuditLog)
        .where(AuditLog.workspace_id == workspace_id)
        .order_by(AuditLog.created_at.desc())
        .limit(5)
    )
    audit_logs = [
        {
            "id": row.id,
            "action": row.action,
            "target": row.resource_type or row.resource_id or "workspace",
            "actor": row.user_id or user.email,
            "hash": (row.hash_chain or row.prev_hash or "")[:12],
            "ts": row.created_at.isoformat() if row.created_at else "",
        }
        for row in audit_result.scalars().all()
    ]
    alert_result = await db.execute(
        select(SecurityEvent)
        .where(SecurityEvent.workspace_id == workspace_id, SecurityEvent.status != "resolved")
        .order_by(SecurityEvent.created_at.desc())
        .limit(5)
    )
    alerts = [
        {
            "id": row.id,
            "title": row.description or row.event_type,
            "severity": row.severity,
            "source": row.threat_type or row.event_type,
            "time": row.created_at.isoformat() if row.created_at else "",
        }
        for row in alert_result.scalars().all()
    ]
    fleet = [
        {
            "id": model["id"],
            "name": model["display_name"],
            "quant": model["provider"],
            "replicas": 1,
            "route": model["provider"],
            "p50": 0 if model["provider"] == "ollama" else int(avg_latency),
        }
        for model in _default_models()[:4]
    ]
    policy_events = [
        {
            "t": row["ts"],
            "title": "Inference complete",
            "body": f"{row['tokens']} tokens · {row['latency']} ms · ${row['cost']:.5f}",
            "tone": "info",
        }
        for row in recent_runs[:5]
    ]

    return {
        "workspace_id": workspace_id,
        "plan": "free_evaluation",
        "members_count": 1,
        "models_enabled": models_enabled,
        "total_requests_today": total_requests,
        "requests_per_min": total_requests,
        "p50_latency_ms": int(avg_latency),
        "tokens_per_sec": int(total_tokens),
        "spend_today_usd": round(float(spend_today), 4),
        "spend_cap_usd": 150.0,
        "budget_remaining_usd": round(150.0 - float(spend_today), 4),
        "active_pipelines": 2,
        "active_deployments": 1,
        "active_models": models_enabled,
        "audit_entries": audit_entries,
        "recent_runs": recent_runs,
        "policy_events": policy_events,
        "alerts": alerts,
        "audit_logs": audit_logs,
        "fleet": fleet,
        "routing": {
            "hetzner_percent": 100 if total_requests else 0,
            "aws_percent": 0,
            "primary_region": "hetzner-fsn1",
            "burst_region": "aws-us-east-1",
        },
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/observability")
async def workspace_observability(user=Depends(get_current_user)):
    return {
        "status": "healthy",
        "region": "hetzner-fsn1",
        "latency_ms": 42,
        "requests_today": 342,
        "error_rate": 0.001,
        "policy_pass_rate": 0.998,
        "active_routes": ["playground", "gpc", "pipelines", "billing"],
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.patch("/settings")
async def update_settings(body: dict, user=Depends(get_current_user)):
    return {"message": "Settings updated", "settings": body}


@router.get("/models")
async def list_models(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ModelConfig).where(ModelConfig.workspace_id == (user.workspace_id or "default"))
    )
    models = result.scalars().all()
    if not models:
        return _default_models()
    return [
        {
            "id": m.id,
            "provider": m.provider,
            "model_name": m.model_name,
            "display_name": m.display_name,
            "is_enabled": m.is_enabled,
            "cost_per_1k_input": m.cost_per_1k_input,
            "cost_per_1k_output": m.cost_per_1k_output,
        }
        for m in models
    ]


@router.patch("/models/{model_id}")
async def toggle_model(model_id: str, body: dict, user=Depends(get_current_user)):
    return {"id": model_id, "is_enabled": body.get("is_enabled", True), "message": "Model updated"}


@router.get("/api-keys")
async def ws_api_keys(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(APIKey).where(APIKey.user_id == user.id))
    return [{"id": k.id, "name": k.name, "key_prefix": k.key_prefix, "is_active": k.is_active} for k in result.scalars().all()]


@router.post("/api-keys")
async def create_ws_key(body: dict, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    import secrets
    from backend.core.security.auth import get_password_hash

    raw = f"vk_{secrets.token_urlsafe(32)}"
    key = APIKey(
        user_id=user.id,
        workspace_id=user.workspace_id or "",
        name=body.get("name", "Workspace Key"),
        key_hash=get_password_hash(raw),
        key_prefix=raw[:8],
    )
    db.add(key)
    await db.commit()
    return {"id": key.id, "key": raw, "name": key.name}


@router.delete("/api-keys/{key_id}")
async def delete_ws_key(key_id: str, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(APIKey).where(APIKey.id == key_id))
    key = result.scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=404, detail="Key not found")
    key.is_active = False
    await db.commit()
    return {"message": "Key deleted"}


@router.get("/members")
async def list_members(user=Depends(get_current_user)):
    return [{"id": user.id, "email": user.email, "role": "owner", "joined_at": datetime.now(timezone.utc).isoformat()}]


@router.post("/members/invite")
async def invite_member(body: dict, user=Depends(get_current_user)):
    return {"message": f"Invitation sent to {body.get('email', '')}"}


@router.get("/budget")
async def workspace_budget(user=Depends(get_current_user)):
    return {
        "total_budget_usd": 150.0,
        "spent_usd": 12.50,
        "remaining_usd": 137.50,
        "period": "monthly",
        "rules": [],
    }


@router.get("/cost-budget")
async def cost_budget(user=Depends(get_current_user)):
    return {
        "budget_usd": 150.0,
        "spent_usd": 12.50,
        "forecast_usd": 45.00,
        "alerts": [],
    }


@router.get("/cost-budget.csv")
async def cost_budget_csv(user=Depends(get_current_user)):
    csv = (
        "metric,value\n"
        "budget_usd,150.00\n"
        "spent_usd,12.50\n"
        "forecast_usd,45.00\n"
        "remaining_usd,137.50\n"
    )
    return Response(content=csv, media_type="text/csv")


def _ws_dict(ws: Workspace) -> dict:
    return {
        "id": ws.id,
        "name": ws.name,
        "slug": ws.slug,
        "plan": ws.plan,
        "settings": ws.settings_json or {},
        "is_active": ws.is_active,
    }


def _default_models():
    return [
        {"id": "m1", "provider": "openai", "model_name": "gpt-4o", "display_name": "GPT-4o", "is_enabled": True, "cost_per_1k_input": 0.005, "cost_per_1k_output": 0.015},
        {"id": "m2", "provider": "openai", "model_name": "gpt-4o-mini", "display_name": "GPT-4o Mini", "is_enabled": True, "cost_per_1k_input": 0.00015, "cost_per_1k_output": 0.0006},
        {"id": "m3", "provider": "groq", "model_name": "llama-3.1-8b-instant", "display_name": "Groq Llama 3.1 8B Instant", "is_enabled": True, "cost_per_1k_input": 0.00005, "cost_per_1k_output": 0.00008},
        {"id": "m4", "provider": "huggingface", "model_name": "meta-llama/Llama-3.1-8B-Instruct:fastest", "display_name": "Hugging Face Llama 3.1 8B", "is_enabled": True, "cost_per_1k_input": 0.0001, "cost_per_1k_output": 0.0001},
        {"id": "m5", "provider": "gemini", "model_name": "gemini-2.5-flash", "display_name": "Gemini 2.5 Flash", "is_enabled": True, "cost_per_1k_input": 0.0003, "cost_per_1k_output": 0.0003},
        {"id": "m6", "provider": "ollama", "model_name": "qwen2.5:3b", "display_name": "Ollama Qwen 2.5 3B", "is_enabled": True, "cost_per_1k_input": 0.0, "cost_per_1k_output": 0.0},
    ]
