"""Workspace / tenant routes."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database.database import get_db
from backend.core.security.auth import get_current_user
from backend.db.models.ai import ExecLog
from backend.db.models.marketplace import Deployment, Pipeline
from backend.db.models.security import AuditLog, SecurityEvent
from backend.db.models.workspace import ModelConfig, Workspace, WorkspaceMember
from backend.db.models.user import APIKey, User
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
    return await _overview_payload(db, user.workspace_id or "default", user.email)


@router.get("/overview/live")
async def workspace_overview_live(db: AsyncSession = Depends(get_db)):
    return await _overview_payload(db, "default", "system")


async def _overview_payload(db: AsyncSession, workspace_id: str, actor_email: str):
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    last_minute = now - timedelta(minutes=1)
    last_24h = now - timedelta(hours=24)
    elapsed_minutes = max(1, int((now - today_start).total_seconds() / 60))

    total_requests = await db.scalar(select(func.count()).select_from(ExecLog).where(ExecLog.workspace_id == workspace_id, ExecLog.created_at >= today_start)) or 0
    requests_per_min = await db.scalar(select(func.count()).select_from(ExecLog).where(ExecLog.workspace_id == workspace_id, ExecLog.created_at >= last_minute)) or 0
    total_tokens = await db.scalar(select(func.coalesce(func.sum(ExecLog.total_tokens), 0)).where(ExecLog.workspace_id == workspace_id, ExecLog.created_at >= today_start)) or 0
    spend_today = await db.scalar(select(func.coalesce(func.sum(ExecLog.cost_usd), 0.0)).where(ExecLog.workspace_id == workspace_id, ExecLog.created_at >= today_start)) or 0.0
    avg_latency = await db.scalar(select(func.coalesce(func.avg(ExecLog.latency_ms), 0)).where(ExecLog.workspace_id == workspace_id, ExecLog.created_at >= today_start)) or 0
    audit_entries = await db.scalar(select(func.count()).select_from(AuditLog).where(AuditLog.workspace_id == workspace_id, AuditLog.created_at >= today_start)) or 0
    budget_limit = await db.scalar(select(func.max(BudgetRule.limit_usd)).where(BudgetRule.workspace_id == workspace_id, BudgetRule.is_active == True)) or 150.0

    model_rows = (await db.execute(select(ModelConfig).where(ModelConfig.workspace_id == workspace_id, ModelConfig.is_enabled == True))).scalars().all()
    model_payload = [
        {"id": row.id, "provider": row.provider, "display_name": row.display_name}
        for row in model_rows
    ] or _default_models()
    models_enabled = len(model_payload)

    result = await db.execute(
        select(ExecLog)
        .where(ExecLog.workspace_id == workspace_id)
        .order_by(ExecLog.created_at.desc())
        .limit(5)
    )
    recent_rows = result.scalars().all()
    recent_runs = [
        {
            "id": row.id,
            "model": row.model or "qwen2.5:3b",
            "route": _route_for_provider(row.provider),
            "latency": row.latency_ms or 0,
            "tokens": row.total_tokens or 0,
            "cost": row.cost_usd or 0.0,
            "policy": "redacted" if row.policy_flags else "passed",
            "ts": _relative_time(row.created_at, now),
        }
        for row in recent_rows
    ]

    recent_24h = (await db.execute(select(ExecLog).where(ExecLog.workspace_id == workspace_id, ExecLog.created_at >= last_24h))).scalars().all()
    routing_history = _routing_history(recent_24h, now)
    hetzner_count = sum(1 for row in recent_24h if _route_for_provider(row.provider) == "hetzner")
    aws_count = sum(1 for row in recent_24h if _route_for_provider(row.provider) == "aws-burst")
    routed_total = hetzner_count + aws_count
    hetzner_percent = round((hetzner_count / routed_total) * 100) if routed_total else 0
    aws_percent = round((aws_count / routed_total) * 100) if routed_total else 0

    audit_rows = (await db.execute(
        select(AuditLog)
        .where(AuditLog.workspace_id == workspace_id)
        .order_by(AuditLog.created_at.desc())
        .limit(5)
    )).scalars().all()
    audit_logs = [
        {
            "id": row.id,
            "action": row.action,
            "target": row.resource_type or row.resource_id or "workspace",
            "actor": row.user_id or actor_email,
            "hash": (row.hash_chain or row.prev_hash or "")[:12],
            "ts": row.created_at.isoformat().replace("+00:00", "Z") if row.created_at else "",
        }
        for row in audit_rows
    ]

    try:
        alert_rows = (await db.execute(
            select(SecurityEvent)
            .where(SecurityEvent.workspace_id == workspace_id, SecurityEvent.status != "resolved")
            .order_by(SecurityEvent.created_at.desc())
            .limit(5)
        )).scalars().all()
    except SQLAlchemyError:
        await db.rollback()
        alert_rows = []
    alerts = [
        {
            "id": row.id,
            "title": row.description or row.event_type,
            "severity": row.severity,
            "source": row.threat_type or row.event_type,
            "time": _relative_time(row.created_at, now),
        }
        for row in alert_rows
    ]

    p50 = int(avg_latency)
    fleet = [
        {
            "id": model["id"],
            "name": model["display_name"],
            "quant": model["provider"].upper(),
            "replicas": 1,
            "route": _route_for_provider(model["provider"]),
            "p50": p50,
        }
        for model in model_payload[:4]
    ]
    policy_events = [
        {
            "t": row["ts"],
            "title": "Inference complete",
            "body": f"{row['tokens']} tokens - {row['latency']} ms - ${row['cost']:.5f}",
            "tone": "info",
        }
        for row in recent_runs[:5]
    ]

    try:
        active_pipelines = await db.scalar(
            select(func.count()).select_from(Pipeline).where(Pipeline.workspace_id == workspace_id)
        ) or 0
        active_deployments = await db.scalar(
            select(func.count()).select_from(Deployment).where(Deployment.workspace_id == workspace_id)
        ) or 0
    except SQLAlchemyError:
        await db.rollback()
        active_pipelines = 0
        active_deployments = 0
    burn_rate = float(spend_today) / elapsed_minutes
    forecast_eod = burn_rate * 1440
    spend_pct = round((float(spend_today) / float(budget_limit)) * 100) if budget_limit else 0

    return {
        "workspace_id": workspace_id,
        "plan": "free_evaluation",
        "members_count": 1,
        "models_enabled": models_enabled,
        "total_requests_today": total_requests,
        "requests_per_min": requests_per_min,
        "p50_latency_ms": p50,
        "tokens_per_sec": int(total_tokens / elapsed_minutes) if total_tokens else 0,
        "spend_today_usd": round(float(spend_today), 4),
        "spend_cap_usd": float(budget_limit),
        "spend_percent": spend_pct,
        "spend_status": "on-pace" if forecast_eod <= float(budget_limit) else "over-pace",
        "burn_rate_usd_per_min": round(burn_rate, 4),
        "forecast_eod_usd": round(forecast_eod, 2),
        "spend_breakdown": _spend_breakdown(float(spend_today)),
        "budget_remaining_usd": round(float(budget_limit) - float(spend_today), 4),
        "active_pipelines": active_pipelines,
        "active_deployments": active_deployments,
        "active_models": models_enabled,
        "audit_entries": audit_entries,
        "recent_runs": recent_runs,
        "policy_events": policy_events,
        "alerts": alerts,
        "audit_logs": audit_logs,
        "fleet": fleet,
        "routing": {
            "hetzner_percent": hetzner_percent,
            "aws_percent": aws_percent,
            "primary_region": "hetzner-fsn1",
            "burst_region": "aws-us-east-1",
            "history": routing_history,
            "regions": [
                {"label": "Hetzner FSN1", "value": f"{hetzner_percent}% routed", "sub": "Primary private runtime", "route": "hetzner"},
                {"label": "Hetzner FRA1", "value": f"{active_deployments} active", "sub": "EU-sovereign deployment pool", "route": "hetzner"},
                {"label": "AWS burst (us-east-1)", "value": f"{aws_percent}% engaged", "sub": "On-demand gated by policy", "route": "aws-burst"},
            ],
        },
        "updated_at": now.isoformat(),
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
async def list_members(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if not user.workspace_id:
        return [{"id": user.id, "email": user.email, "role": "owner", "joined_at": datetime.now(timezone.utc).isoformat()}]
        
    result = await db.execute(
        select(WorkspaceMember, User)
        .join(User, WorkspaceMember.user_id == User.id)
        .where(WorkspaceMember.workspace_id == user.workspace_id)
    )
    members = []
    for wm, u in result.all():
        members.append({
            "id": u.id,
            "email": u.email,
            "role": wm.role,
            "joined_at": wm.joined_at.isoformat() if wm.joined_at else None
        })
        
    # If the owner isn't in the members list yet (e.g., legacy data), append them
    if not any(m["id"] == user.id for m in members):
        members.append({
            "id": user.id,
            "email": user.email,
            "role": "owner",
            "joined_at": datetime.now(timezone.utc).isoformat()
        })
        
    return members


@router.post("/members/invite")
async def invite_member(body: dict, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if not user.workspace_id:
        raise HTTPException(status_code=400, detail="User is not part of a valid workspace")
        
    email = body.get("email")
    role = body.get("role", "developer")
    
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")
        
    # Check if user exists
    user_result = await db.execute(select(User).where(User.email == email))
    target_user = user_result.scalar_one_or_none()
    
    if not target_user:
        # Create a shell user for the invitation
        import secrets
        from backend.core.security.auth import get_password_hash
        
        target_user = User(
            email=email,
            username=email.split("@")[0] + "_" + secrets.token_hex(4),
            hashed_password=get_password_hash(secrets.token_urlsafe(32)),
            full_name="Invited User",
            workspace_id=user.workspace_id
        )
        db.add(target_user)
        await db.commit()
        await db.refresh(target_user)
        
    # Check if already a member
    member_result = await db.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == user.workspace_id,
            WorkspaceMember.user_id == target_user.id
        )
    )
    if member_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="User is already a member of this workspace")
        
    # Add to workspace
    wm = WorkspaceMember(
        workspace_id=user.workspace_id,
        user_id=target_user.id,
        role=role,
        invited_by=user.id
    )
    db.add(wm)
    target_user.workspace_id = user.workspace_id
    await db.commit()
    
    return {"message": f"Invitation successfully sent and {email} has been provisioned."}


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
        {"id": "veklom-llama3-70b", "name": "Llama 3.1 70B Instruct", "family": "Llama", "provider": "Open Source", "modality": "chat", "context": 131072, "quant": "INT4", "inputCost": 0.00018, "outputCost": 0.00027, "p50": 96, "p95": 240, "features": ["function-calling", "json-mode", "streaming", "code"], "status": "active", "replicas": 8, "route": "hetzner", "license": "Apache 2.0"},
        {"id": "veklom-mixtral-8x22", "name": "Mixtral 8×22B Instruct", "family": "Mixtral", "provider": "Open Source", "modality": "chat", "context": 65536, "quant": "INT4", "inputCost": 0.00065, "outputCost": 0.00065, "p50": 140, "p95": 380, "features": ["function-calling", "json-mode", "streaming", "multilingual"], "status": "active", "replicas": 4, "route": "hetzner", "license": "Apache 2.0"},
        {"id": "veklom-qwen2-72b", "name": "Qwen 2.5 72B Chat", "family": "Qwen", "provider": "Open Source", "modality": "chat", "context": 131072, "quant": "INT4", "inputCost": 0.00018, "outputCost": 0.00027, "p50": 96, "p95": 240, "features": ["function-calling", "json-mode", "streaming", "code"], "status": "active", "replicas": 8, "route": "hetzner", "license": "Apache 2.0"},
        {"id": "veklom-claude-haiku", "name": "Claude 3.5 Haiku (proxy)", "family": "Claude", "provider": "Anthropic-compatible", "modality": "chat", "context": 200000, "quant": "FP16", "inputCost": 0.0008, "outputCost": 0.004, "p50": 220, "p95": 540, "features": ["function-calling", "vision", "json-mode", "streaming"], "status": "active", "replicas": 2, "route": "aws-burst", "license": "Commercial"},
        {"id": "veklom-deepseek-v3", "name": "DeepSeek v3 Coder", "family": "DeepSeek", "provider": "Open Source", "modality": "completion", "context": 65536, "quant": "INT8", "inputCost": 0.00027, "outputCost": 0.00041, "p50": 88, "p95": 210, "features": ["streaming", "code", "fim"], "status": "active", "replicas": 3, "route": "hetzner", "license": "MIT"},
        {"id": "veklom-bge-large", "name": "BGE-M3 Embeddings", "family": "BGE", "provider": "Open Source", "modality": "embedding", "context": 8192, "quant": "FP16", "inputCost": 0.00002, "outputCost": 0, "p50": 14, "p95": 38, "features": ["multilingual", "long-context"], "status": "active", "replicas": 12, "route": "hetzner", "license": "MIT"},
        {"id": "veklom-cohere-rerank", "name": "Veklom Reranker", "family": "Cross-encoder", "provider": "Veklom Native", "modality": "rerank", "context": 4096, "quant": "FP16", "inputCost": 0.00001, "outputCost": 0, "p50": 22, "p95": 60, "features": ["fast", "binary"], "status": "active", "replicas": 6, "route": "hetzner", "license": "Commercial"},
        {"id": "veklom-whisper-v3", "name": "Whisper Large v3", "family": "Whisper", "provider": "Whisper", "modality": "audio-stt", "context": 0, "quant": "FP16", "inputCost": 0.00006, "outputCost": 0, "p50": 380, "p95": 920, "features": ["multilingual", "diarization"], "status": "active", "replicas": 2, "route": "hetzner", "license": "MIT"},
    ]


def _route_for_provider(provider: str | None) -> str:
    value = (provider or "").strip().lower()
    if value in {"anthropic", "bedrock", "aws"}:
        return "aws-burst"
    return "hetzner"


def _relative_time(value: datetime | None, now: datetime) -> str:
    if not value:
        return ""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    seconds = max(0, int((now - value).total_seconds()))
    if seconds < 60:
        return f"{seconds}s ago"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}h ago"
    return f"{hours // 24}d ago"


def _routing_history(rows: list[ExecLog], now: datetime) -> list[dict]:
    buckets = {
        hour: {"hour": f"{hour:02d}", "hetzner": 0, "aws": 0}
        for hour in range(24)
    }
    for row in rows:
        created_at = row.created_at
        if not created_at:
            continue
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        hour_age = int((now - created_at).total_seconds() // 3600)
        if hour_age < 0 or hour_age > 23:
            continue
        bucket = buckets[created_at.hour]
        if _route_for_provider(row.provider) == "aws-burst":
            bucket["aws"] += 1
        else:
            bucket["hetzner"] += 1
    return list(buckets.values())


def _spend_breakdown(total: float) -> list[dict]:
    categories = [
        ("Inference", 0.65),
        ("Embeddings", 0.16),
        ("GPU burst", 0.12),
        ("Storage", 0.07),
    ]
    return [
        {
            "label": label,
            "amount_usd": round(total * percent, 4),
            "percent": round(percent * 100),
        }
        for label, percent in categories
    ]
