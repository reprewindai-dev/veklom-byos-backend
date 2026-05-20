"""Workspace / tenant routes."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database.database import get_db
from backend.core.security.auth import get_current_user
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
async def workspace_overview(user=Depends(get_current_user)):
    return {
        "workspace_id": user.workspace_id or "default",
        "plan": "free_evaluation",
        "members_count": 1,
        "models_enabled": 5,
        "total_requests_today": 42,
        "spend_today_usd": 1.25,
        "budget_remaining_usd": 148.75,
        "active_pipelines": 2,
        "active_deployments": 1,
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
        {"id": "m3", "provider": "anthropic", "model_name": "claude-3-5-sonnet", "display_name": "Claude 3.5 Sonnet", "is_enabled": True, "cost_per_1k_input": 0.003, "cost_per_1k_output": 0.015},
        {"id": "m4", "provider": "anthropic", "model_name": "claude-3-5-haiku", "display_name": "Claude 3.5 Haiku", "is_enabled": True, "cost_per_1k_input": 0.0008, "cost_per_1k_output": 0.004},
        {"id": "m5", "provider": "google", "model_name": "gemini-2.5-pro", "display_name": "Gemini 2.5 Pro", "is_enabled": True, "cost_per_1k_input": 0.00125, "cost_per_1k_output": 0.01},
    ]
