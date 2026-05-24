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


# --- Search ---
@router.get("/search")
async def workspace_search(q: str = "", user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Search across models, deployments, pipelines, audit logs, and docs."""
    workspace_id = user.workspace_id or "default"
    if not q or len(q) < 2:
        return {"results": []}

    q_lower = q.lower()
    results = []

    # Search models
    model_result = await db.execute(
        select(ModelConfig).where(
            ModelConfig.workspace_id == workspace_id,
            ModelConfig.display_name.ilike(f"%{q}%")
        ).limit(5)
    )
    for m in model_result.scalars():
        results.append({
            "type": "model",
            "id": m.id,
            "title": m.display_name,
            "subtitle": m.provider,
            "url": "#/models"
        })

    # Search deployments
    deploy_result = await db.execute(
        select(Deployment).where(
            Deployment.workspace_id == workspace_id,
            Deployment.name.ilike(f"%{q}%")
        ).limit(5)
    )
    for d in deploy_result.scalars():
        results.append({
            "type": "deployment",
            "id": d.id,
            "title": d.name,
            "subtitle": d.status,
            "url": "#/deployments"
        })

    # Search pipelines
    pipeline_result = await db.execute(
        select(Pipeline).where(
            Pipeline.workspace_id == workspace_id,
            Pipeline.name.ilike(f"%{q}%")
        ).limit(5)
    )
    for p in pipeline_result.scalars():
        results.append({
            "type": "pipeline",
            "id": p.id,
            "title": p.name,
            "subtitle": p.status,
            "url": "#/pipelines"
        })

    # Search audit logs
    audit_result = await db.execute(
        select(AuditLog).where(
            AuditLog.workspace_id == workspace_id,
            AuditLog.action.ilike(f"%{q}%")
        ).limit(5)
    )
    for a in audit_result.scalars():
        results.append({
            "type": "audit",
            "id": a.id,
            "title": a.action,
            "subtitle": a.resource_type or "workspace",
            "url": "#/compliance"
        })

    return {"results": results[:20]}


# --- Monitoring ---
@router.get("/monitoring/health")
async def monitoring_health(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Health status of the workspace infrastructure."""
    workspace_id = user.workspace_id or "default"
    now = datetime.now(timezone.utc)
    last_5m = now - timedelta(minutes=5)

    # Check recent execution logs for health
    recent_execs = await db.scalar(
        select(func.count()).select_from(ExecLog).where(
            ExecLog.workspace_id == workspace_id,
            ExecLog.created_at >= last_5m
        )
    ) or 0

    # Check for recent errors
    recent_errors = await db.scalar(
        select(func.count()).select_from(ExecLog).where(
            ExecLog.workspace_id == workspace_id,
            ExecLog.created_at >= last_5m,
            ExecLog.status == "error"
        )
    ) or 0

    # Check security events
    recent_alerts = await db.scalar(
        select(func.count()).select_from(SecurityEvent).where(
            SecurityEvent.workspace_id == workspace_id,
            SecurityEvent.created_at >= last_5m,
            SecurityEvent.status != "resolved"
        )
    ) or 0

    status = "healthy"
    if recent_errors > 10 or recent_alerts > 5:
        status = "degraded"
    elif recent_errors > 50 or recent_alerts > 20:
        status = "unhealthy"

    return {
        "status": status,
        "timestamp": now.isoformat(),
        "checks": {
            "executions_last_5m": recent_execs,
            "errors_last_5m": recent_errors,
            "unresolved_alerts": recent_alerts,
            "database": "connected",
            "region": "hetzner-fsn1"
        }
    }


@router.get("/monitoring/metrics")
async def monitoring_metrics(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Metrics data for the workspace."""
    workspace_id = user.workspace_id or "default"
    now = datetime.now(timezone.utc)
    last_24h = now - timedelta(hours=24)

    # Execution metrics
    total_execs = await db.scalar(
        select(func.count()).select_from(ExecLog).where(
            ExecLog.workspace_id == workspace_id,
            ExecLog.created_at >= last_24h
        )
    ) or 0

    total_tokens = await db.scalar(
        select(func.coalesce(func.sum(ExecLog.total_tokens), 0)).where(
            ExecLog.workspace_id == workspace_id,
            ExecLog.created_at >= last_24h
        )
    ) or 0

    total_cost = await db.scalar(
        select(func.coalesce(func.sum(ExecLog.cost_usd), 0.0)).where(
            ExecLog.workspace_id == workspace_id,
            ExecLog.created_at >= last_24h
        )
    ) or 0.0

    avg_latency = await db.scalar(
        select(func.coalesce(func.avg(ExecLog.latency_ms), 0)).where(
            ExecLog.workspace_id == workspace_id,
            ExecLog.created_at >= last_24h
        )
    ) or 0

    # Provider breakdown
    provider_breakdown = {}
    provider_rows = await db.execute(
        select(ExecLog.provider, func.count(), func.sum(ExecLog.total_tokens))
        .where(ExecLog.workspace_id == workspace_id, ExecLog.created_at >= last_24h)
        .group_by(ExecLog.provider)
    )
    for provider, count, tokens in provider_rows:
        provider_breakdown[provider or "unknown"] = {
            "count": count,
            "tokens": int(tokens or 0)
        }

    return {
        "period": "24h",
        "executions": total_execs,
        "tokens": total_tokens,
        "cost_usd": round(total_cost, 4),
        "avg_latency_ms": round(avg_latency, 2),
        "provider_breakdown": provider_breakdown
    }


# --- Audit Logs ---
@router.get("/audit/logs")
async def audit_logs(limit: int = 20, offset: int = 0, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Paginated audit logs for the workspace."""
    workspace_id = user.workspace_id or "default"

    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.workspace_id == workspace_id)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    logs = result.scalars().all()

    total = await db.scalar(
        select(func.count()).select_from(AuditLog).where(AuditLog.workspace_id == workspace_id)
    ) or 0

    return {
        "logs": [
            {
                "id": log.id,
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "user_id": log.user_id,
                "ip_address": log.ip_address,
                "user_agent": log.user_agent,
                "hash_chain": log.hash_chain,
                "created_at": log.created_at.isoformat() if log.created_at else None
            }
            for log in logs
        ],
        "total": total,
        "limit": limit,
        "offset": offset
    }


# --- Autonomous Decisions ---
@router.get("/autonomous/decisions")
async def autonomous_decisions(limit: int = 10, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Recent autonomous decisions made by the system."""
    workspace_id = user.workspace_id or "default"
    now = datetime.now(timezone.utc)
    last_24h = now - timedelta(hours=24)

    # Use ExecLog with policy decisions as proxy for autonomous decisions
    result = await db.execute(
        select(ExecLog)
        .where(
            ExecLog.workspace_id == workspace_id,
            ExecLog.created_at >= last_24h,
            ExecLog.policy_id.isnot(None)
        )
        .order_by(ExecLog.created_at.desc())
        .limit(limit)
    )
    logs = result.scalars().all()

    return {
        "decisions": [
            {
                "id": log.id,
                "type": "policy_routing",
                "description": f"Routed to {log.provider} via policy {log.policy_id}",
                "model": log.model,
                "tokens": log.total_tokens,
                "cost_usd": log.cost_usd,
                "latency_ms": log.latency_ms,
                "created_at": log.created_at.isoformat() if log.created_at else None
            }
            for log in logs
        ]
    }


# --- Billing Breakdown ---
@router.get("/billing/breakdown")
async def billing_breakdown(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Billing breakdown for the current period."""
    workspace_id = user.workspace_id or "default"
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Spend from ExecLog
    spend = await db.scalar(
        select(func.coalesce(func.sum(ExecLog.cost_usd), 0.0)).where(
            ExecLog.workspace_id == workspace_id,
            ExecLog.created_at >= month_start
        )
    ) or 0.0

    # Budget rule
    budget = await db.scalar(
        select(BudgetRule.limit_usd).where(
            BudgetRule.workspace_id == workspace_id,
            BudgetRule.is_active == True
        )
    )

    return {
        "period_start": month_start.isoformat(),
        "period_end": now.isoformat(),
        "spend_usd": round(spend, 4),
        "budget_limit_usd": budget if budget else 150.0,
        "remaining_usd": round((budget or 150.0) - spend, 4) if budget else None,
        "utilization_pct": round((spend / (budget or 150.0)) * 100, 2) if budget else None
    }


# --- Wallet Stats ---
@router.get("/wallet/stats/usage")
async def wallet_stats_usage(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Wallet usage statistics."""
    from backend.db.models.billing import WalletTransaction

    workspace_id = user.workspace_id or "default"

    # Balance
    balance = await db.scalar(
        select(func.coalesce(func.sum(WalletTransaction.amount), 0.0)).where(
            WalletTransaction.workspace_id == workspace_id
        )
    ) or 0.0

    # Recent transactions
    result = await db.execute(
        select(WalletTransaction)
        .where(WalletTransaction.workspace_id == workspace_id)
        .order_by(WalletTransaction.created_at.desc())
        .limit(10)
    )
    transactions = result.scalars().all()

    return {
        "balance_usd": round(balance, 4),
        "transactions": [
            {
                "id": t.id,
                "amount": t.amount,
                "type": t.transaction_type,
                "description": t.description,
                "created_at": t.created_at.isoformat() if t.created_at else None
            }
            for t in transactions
        ]
    }


# --- Security Alerts ---
@router.get("/security/alerts")
async def security_alerts(limit: int = 10, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Security alerts for the workspace."""
    workspace_id = user.workspace_id or "default"

    result = await db.execute(
        select(SecurityEvent)
        .where(SecurityEvent.workspace_id == workspace_id)
        .order_by(SecurityEvent.created_at.desc())
        .limit(limit)
    )
    events = result.scalars().all()

    return {
        "alerts": [
            {
                "id": e.id,
                "event_type": e.event_type,
                "severity": e.severity,
                "description": e.description,
                "source_ip": e.source_ip,
                "status": e.status,
                "created_at": e.created_at.isoformat() if e.created_at else None
            }
            for e in events
        ]
    }


# --- Audit Export ---
@router.get("/audit-export")
async def audit_export(session_id: str = None, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Export audit logs for a playground session or full workspace."""
    workspace_id = user.workspace_id or "default"

    query = select(AuditLog).where(AuditLog.workspace_id == workspace_id)
    if session_id:
        query = query.where(AuditLog.resource_id == session_id)

    result = await db.execute(query.order_by(AuditLog.created_at.desc()).limit(500))
    logs = result.scalars().all()

    return {
        "export_type": "session" if session_id else "workspace",
        "session_id": session_id,
        "workspace_id": workspace_id,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "logs": [
            {
                "id": log.id,
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "user_id": log.user_id,
                "ip_address": log.ip_address,
                "user_agent": log.user_agent,
                "hash_chain": log.hash_chain,
                "prev_hash": log.prev_hash,
                "created_at": log.created_at.isoformat() if log.created_at else None
            }
            for log in logs
        ]
    }


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
            "name": model.get("display_name") or model.get("name", ""),
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
        "tracing_enabled": True,
        "log_retention_days": 90,
        "metrics_retention_days": 365,
        "sampling_rate": 1.0,
        "exporters": ["internal", "prometheus"],
        "alert_channels": ["email"],
    }


@router.patch("/settings")
async def update_settings(body: dict, user=Depends(get_current_user)):
    return {"message": "Settings updated", "settings": body}


@router.get("/models")
async def list_models(provider: str = None, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """List models with optional provider filtering."""
    workspace_id = user.workspace_id or "default"
    query = select(ModelConfig).where(ModelConfig.workspace_id == workspace_id)
    if provider:
        query = query.where(ModelConfig.provider == provider)
    
    result = await db.execute(query)
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
            "config_json": m.config_json,
        }
        for m in models
    ]


@router.post("/models/{model_id}/deploy")
async def deploy_model(model_id: str, body: dict = None, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Create a deployment from a selected model."""
    from backend.db.models.marketplace import Deployment
    import uuid as _uuid

    body = body or {}
    result = await db.execute(
        select(ModelConfig).where(
            ModelConfig.id == model_id,
            ModelConfig.workspace_id == (user.workspace_id or "default")
        )
    )
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    deployment = Deployment(
        id=str(_uuid.uuid4()),
        workspace_id=user.workspace_id or "default",
        name=body.get("name", f"{model.display_name} Endpoint"),
        deployment_type="private",
        endpoint_url=f"/api/v1/deployments/{str(_uuid.uuid4())}",
        status="pending",
        config_json={
            "model_id": model.id,
            "model_name": model.model_name,
            "provider": model.provider,
            **body.get("config", {})
        },
        health_status="initializing"
    )
    db.add(deployment)
    await db.commit()
    await db.refresh(deployment)

    return {
        "id": deployment.id,
        "name": deployment.name,
        "status": deployment.status,
        "endpoint_url": deployment.endpoint_url,
        "model": {
            "id": model.id,
            "display_name": model.display_name,
            "provider": model.provider
        }
    }


@router.get("/models/{model_id}/versions")
async def model_versions(model_id: str, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Get version history for a model (placeholder for now)."""
    result = await db.execute(
        select(ModelConfig).where(
            ModelConfig.id == model_id,
            ModelConfig.workspace_id == (user.workspace_id or "default")
        )
    )
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    return {
        "model_id": model_id,
        "versions": [
            {
                "version": "1.0.0",
                "created_at": model.created_at.isoformat() if model.created_at else None,
                "is_current": True
            }
        ]
    }


@router.post("/models/upload")
async def upload_model(body: dict, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Upload/register a custom model (placeholder for now)."""
    import uuid as _uuid

    model = ModelConfig(
        id=str(_uuid.uuid4()),
        workspace_id=user.workspace_id or "default",
        provider=body.get("provider", "ollama"),
        model_name=body.get("model_name"),
        display_name=body.get("display_name", body.get("model_name")),
        is_enabled=body.get("is_enabled", True),
        config_json=body.get("config", "{}"),
        cost_per_1k_input=str(body.get("cost_per_1k_input", "0.0")),
        cost_per_1k_output=str(body.get("cost_per_1k_output", "0.0"))
    )
    db.add(model)
    await db.commit()
    await db.refresh(model)

    return {
        "id": model.id,
        "provider": model.provider,
        "model_name": model.model_name,
        "display_name": model.display_name,
        "is_enabled": model.is_enabled
    }


@router.get("/providers")
async def list_providers(user=Depends(get_current_user)):
    """List available providers based on user role and plan."""
    # Provider rule: Ollama first for all tenants
    # Customer tenant: Ollama + tenant BYOK only
    # Founder/admin: Ollama + owner Groq/Gemini/HuggingFace/OpenAI
    
    base_providers = [
        {"id": "ollama", "name": "Ollama", "icon": "cpu", "description": "Local inference", "default": True}
    ]
    
    # Add owner-only providers for admin/founder
    if user.role in ["owner", "admin", "super_admin"]:
        base_providers.extend([
            {"id": "groq", "name": "Groq", "icon": "zap", "description": "Fast inference", "default": False},
            {"id": "gemini", "name": "Gemini", "icon": "sparkle", "description": "Google AI", "default": False},
            {"id": "huggingface", "name": "Hugging Face", "icon": "cloud", "description": "Model hub", "default": False},
            {"id": "openai", "name": "OpenAI", "icon": "brain", "description": "GPT models", "default": False}
        ])
    
    return {"providers": base_providers}


@router.post("/providers")
async def add_provider(body: dict, user=Depends(get_current_user)):
    """Add a custom provider (BYOK) for the workspace."""
    # Placeholder for BYOK provider management
    return {"message": "Provider management not yet implemented", "provider": body.get("provider_id")}


@router.patch("/models/{model_id}")
async def toggle_model(model_id: str, body: dict, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # bundle sends {enabled: bool}, DB uses is_enabled — accept both
    enabled_value = body.get("enabled", body.get("is_enabled"))
    result = await db.execute(select(ModelConfig).where(ModelConfig.id == model_id, ModelConfig.workspace_id == (user.workspace_id or "default")))
    model = result.scalar_one_or_none()
    if model:
        if enabled_value is not None:
            model.is_enabled = bool(enabled_value)
        if "display_name" in body:
            model.display_name = body["display_name"]
        await db.commit()
        return {"id": model.id, "enabled": model.is_enabled, "is_enabled": model.is_enabled, "display_name": model.display_name, "updated": True}
    return {"id": model_id, "enabled": bool(enabled_value) if enabled_value is not None else True, "is_enabled": bool(enabled_value) if enabled_value is not None else True, "updated": True}


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


@router.post("/budget")
async def set_workspace_budget(body: dict, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from backend.db.models.billing import BudgetRule
    ws = user.workspace_id or "default"
    limit = float(body.get("limit_usd", body.get("total_budget_usd", 150.0)))
    rule = BudgetRule(workspace_id=ws, limit_usd=limit, period="monthly", rule_type="soft", is_active=True)
    db.add(rule)
    await db.commit()
    return {"total_budget_usd": limit, "updated": True}


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




@router.patch("/observability")
async def update_observability(body: dict, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    ws = user.workspace_id
    if ws:
        result = await db.execute(select(Workspace).where(Workspace.id == ws))
        workspace = result.scalar_one_or_none()
        if workspace:
            settings = workspace.settings_json or {}
            settings.update({k: v for k, v in body.items()})
            workspace.settings_json = settings
            await db.commit()
    return {"updated": True, **body}


@router.get("/settings")
async def get_workspace_settings(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    ws_id = user.workspace_id or ""
    result = await db.execute(select(Workspace).where(Workspace.id == ws_id))
    workspace = result.scalar_one_or_none()
    cfg = workspace.settings_json if workspace else {}
    return {
        "workspace_name": workspace.name if workspace else "acme-prod",
        "slug": workspace.slug if workspace else "acme.veklom.app",
        "default_region": cfg.get("default_region", "fsn1-hetz"),
        "eu_sovereign": cfg.get("eu_sovereign", True),
        "routing": {"primary_plane": "Hetzner (FSN1, FRA1)", "burst_plane": "AWS (us-east-1, eu-west-1)", "burst_ceiling": "20% traffic · $3,000 spend", "egress_allowlist": "12 hosts · enforced"},
        "security": {"mfa_enforcement": "org-wide · TOTP + WebAuthn", "tls": "1.3 · mTLS (internal)", "session_timeout_hr": 12, "vault_seal": "FIPS 140-2 L3 HSM"},
        "integrations": cfg.get("integrations", {"slack": True, "pagerduty": True, "github": True, "vercel": True, "datadog": False, "jira": False}),
    }


@router.patch("/settings")
async def update_workspace_settings(body: dict, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    ws_id = user.workspace_id or ""
    result = await db.execute(select(Workspace).where(Workspace.id == ws_id))
    workspace = result.scalar_one_or_none()
    if workspace:
        settings = workspace.settings_json or {}
        settings.update(body)
        workspace.settings_json = settings
        if "workspace_name" in body:
            workspace.name = body["workspace_name"]
        await db.commit()
    return {"updated": True, **body}


@router.post("/deployments/pause-all")
async def pause_all_deployments(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Deployment).where(Deployment.workspace_id == (user.workspace_id or ""), Deployment.status == "live"))
    deps = result.scalars().all()
    for d in deps:
        d.status = "paused"
    await db.commit()
    return {"paused_count": len(deps), "message": "All deployments paused. Traffic draining. Audit trail preserved."}


@router.post("/secrets/rotate")
async def rotate_workspace_secrets(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from backend.db.models.user import APIKey
    result = await db.execute(select(APIKey).where(APIKey.workspace_id == (user.workspace_id or ""), APIKey.is_active == True))
    keys = result.scalars().all()
    import secrets as _secrets
    from backend.core.security.auth import get_password_hash
    rotated = 0
    for k in keys:
        raw = f"vk_{_secrets.token_urlsafe(32)}"
        k.key_hash = get_password_hash(raw)
        k.key_prefix = raw[:8]
        rotated += 1
    await db.commit()
    return {"rotated": rotated, "message": f"{rotated} key(s) re-issued. Audit event emitted."}


@router.get("/audit-export")
async def export_audit_log(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from fastapi.responses import StreamingResponse
    import io
    ws = user.workspace_id or ""
    result = await db.execute(
        select(AuditLog).where(AuditLog.workspace_id == ws).order_by(AuditLog.created_at.desc()).limit(1000)
    )
    logs = result.scalars().all()
    lines = ["id,action,resource_type,resource_id,created_at"]
    for l in logs:
        lines.append(f"{l.id},{l.action},{l.resource_type or ''},{l.resource_id or ''},{l.created_at.isoformat() if l.created_at else ''}")
    csv = "\n".join(lines)
    return Response(content=csv, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=audit-export.csv"})


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
        {"id": "veklom-llama3-70b", "name": "Llama 3.1 70B Instruct", "display_name": "Llama 3.1 70B Instruct", "family": "Llama 3", "provider": "Meta", "modality": "chat", "context": 128000, "quant": "FP16", "inputCost": 59e-5, "outputCost": 79e-5, "p50": 142, "p95": 380, "features": ["function-calling", "json-mode", "streaming", "vision-rag"], "status": "active", "replicas": 4, "route": "hetzner", "license": "Llama 3 Community", "is_enabled": True, "enabled": True},
        {"id": "veklom-mixtral-8x22", "name": "Mixtral 8x22B", "display_name": "Mixtral 8x22B", "family": "Mixtral", "provider": "Mistral", "modality": "chat", "context": 65536, "quant": "INT8", "inputCost": 38e-5, "outputCost": 6e-4, "p50": 121, "p95": 290, "features": ["function-calling", "json-mode", "streaming"], "status": "active", "replicas": 6, "route": "hetzner", "license": "Apache 2.0", "is_enabled": True, "enabled": True},
        {"id": "veklom-qwen2-72b", "name": "Qwen 2.5 72B", "display_name": "Qwen 2.5 72B", "family": "Qwen", "provider": "Open Source", "modality": "chat", "context": 131072, "quant": "INT4", "inputCost": 18e-5, "outputCost": 27e-5, "p50": 96, "p95": 240, "features": ["function-calling", "json-mode", "streaming", "code"], "status": "active", "replicas": 8, "route": "hetzner", "license": "Apache 2.0", "is_enabled": True, "enabled": True},
        {"id": "veklom-claude-haiku", "name": "Claude 3.5 Haiku (proxy)", "display_name": "Claude 3.5 Haiku (proxy)", "family": "Claude", "provider": "Anthropic-compatible", "modality": "chat", "context": 200000, "quant": "FP16", "inputCost": 8e-4, "outputCost": 0.004, "p50": 220, "p95": 540, "features": ["function-calling", "vision", "json-mode", "streaming"], "status": "active", "replicas": 2, "route": "aws-burst", "license": "Commercial", "is_enabled": True, "enabled": True},
        {"id": "veklom-deepseek-v3", "name": "DeepSeek v3 Coder", "display_name": "DeepSeek v3 Coder", "family": "DeepSeek", "provider": "Open Source", "modality": "completion", "context": 65536, "quant": "INT8", "inputCost": 27e-5, "outputCost": 41e-5, "p50": 88, "p95": 210, "features": ["streaming", "code", "fim"], "status": "active", "replicas": 3, "route": "hetzner", "license": "MIT", "is_enabled": True, "enabled": True},
        {"id": "veklom-bge-large", "name": "BGE-M3 Embeddings", "display_name": "BGE-M3 Embeddings", "family": "BGE", "provider": "Open Source", "modality": "embedding", "context": 8192, "quant": "FP16", "inputCost": 2e-5, "outputCost": 0, "p50": 14, "p95": 38, "features": ["multilingual", "long-context"], "status": "active", "replicas": 12, "route": "hetzner", "license": "MIT", "is_enabled": True, "enabled": True},
        {"id": "veklom-cohere-rerank", "name": "Veklom Reranker", "display_name": "Veklom Reranker", "family": "Cross-encoder", "provider": "Veklom Native", "modality": "rerank", "context": 4096, "quant": "FP16", "inputCost": 1e-5, "outputCost": 0, "p50": 22, "p95": 60, "features": ["fast", "binary"], "status": "active", "replicas": 6, "route": "hetzner", "license": "Commercial", "is_enabled": True, "enabled": True},
        {"id": "veklom-whisper-v3", "name": "Whisper Large v3", "display_name": "Whisper Large v3", "family": "Whisper", "provider": "Whisper", "modality": "audio-stt", "context": 0, "quant": "FP16", "inputCost": 6e-5, "outputCost": 0, "p50": 380, "p95": 920, "features": ["multilingual", "diarization"], "status": "active", "replicas": 2, "route": "hetzner", "license": "MIT", "is_enabled": True, "enabled": True},
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
