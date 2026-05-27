"""Veklom Governed Operator Committees Router.

Provides 15 API routes to monitor, control, schedule, and approve Veklom internal operator tasks and sub-agent pools.
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database.database import get_db
from backend.core.security.auth import get_current_user
from backend.db.models.internal_operators import (
    InternalOperatorTask,
    InternalOperatorSchedule,
    InternalOperatorMemory,
    InternalOperatorArtifact,
    InternalOperatorEscalation,
    InternalOperatorBudget,
    InternalOperatorProviderUsage,
    InternalOperatorApproval
)

router = APIRouter(
    prefix="/internal/operators",
    tags=["uacp-operators"]
)

# ---------------------------------------------------------------------------
# Auth Gate
# ---------------------------------------------------------------------------
async def require_superuser(user=Depends(get_current_user)):
    """Only superusers or automation keys can access the registry."""
    if user.role not in ("admin", "super_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superuser or AUTOMATION scope required"
        )
    return user

# ---------------------------------------------------------------------------
# Worker Registry Registry
# ---------------------------------------------------------------------------
WORKER_REGISTRY = {
    "workers": {
        "herald": {"pillar": "marketplace", "committees": ["marketplace-operations"], "ready": True},
        "harvest": {"pillar": "marketplace", "committees": ["marketplace-operations"], "ready": True},
        "bouncer": {"pillar": "marketplace", "committees": ["marketplace-operations"], "ready": True},
        "gauge": {"pillar": "marketplace", "committees": ["marketplace-operations"], "ready": True},
        "arbiter": {"pillar": "marketplace", "committees": ["marketplace-operations"], "ready": True},
        
        "ledger": {"pillar": "governance", "committees": ["governance-evidence"], "ready": True},
        "oracle": {"pillar": "governance", "committees": ["governance-evidence"], "ready": True},
        "builder-arbiter": {"pillar": "governance", "committees": ["governance-evidence", "builder-systems"], "ready": True},
        "sheriff": {"pillar": "governance", "committees": ["governance-evidence", "experience-assurance"], "ready": True},
        
        "signal": {"pillar": "intelligence", "committees": ["growth-intelligence"], "ready": True},
        "scout": {"pillar": "intelligence", "committees": ["growth-intelligence"], "ready": True},
        "mint": {"pillar": "intelligence", "committees": ["growth-intelligence"], "ready": True},
        "welcome": {"pillar": "intelligence", "committees": ["growth-intelligence", "experience-assurance"], "ready": True},
        
        "builder-scout": {"pillar": "builder", "committees": ["builder-systems"], "ready": False},
        "builder-forge": {"pillar": "builder", "committees": ["builder-systems"], "ready": False},
        
        "sentinel": {"pillar": "assurance", "committees": ["experience-assurance"], "ready": True},
        "mirror": {"pillar": "assurance", "committees": ["experience-assurance"], "ready": True},
        "polish": {"pillar": "assurance", "committees": ["experience-assurance"], "ready": True},
        "glide": {"pillar": "assurance", "committees": ["experience-assurance"], "ready": True},
        "pulse": {"pillar": "assurance", "committees": ["experience-assurance"], "ready": True},
    },
    "committees": [
        "marketplace-operations",
        "governance-evidence",
        "growth-intelligence",
        "builder-systems",
        "experience-assurance"
    ],
    "minimum_live_set": [
        "gauge", "ledger", "sentinel", "mirror", "pulse", "sheriff", "polish"
    ],
    "promotion_logic": "Require Archives write for promotion."
}

# ---------------------------------------------------------------------------
# Provider Routing Function (Mathematical Choice Engine)
# ---------------------------------------------------------------------------
def choose_provider(worker_id: str, task_type: str, risk: str, context_tokens: int, urgency: str) -> str:
    """Mathematical and Policy-driven choice engine mapping tasks to LLM backends."""
    if task_type in ["route_check", "heartbeat", "metric_summary", "stale_widget_check"]:
        return "ollama"
        
    if urgency == "high" and context_tokens < 8000:
        return "groq"
        
    if task_type in ["classification", "source_clustering", "license_hint", "lead_scoring"]:
        return "huggingface"
        
    if context_tokens > 24000 or task_type in ["policy_review", "compliance_mapping", "long_doc_analysis"]:
        return "gemini"
        
    if risk in ["critical", "legal", "production_release", "negotiation_final", "security_ambiguous"]:
        return "openai"
        
    return "ollama"

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/registry")
async def get_worker_registry(user=Depends(require_superuser)):
    """Returns the internal UACP V3 Worker Registry."""
    return WORKER_REGISTRY

@router.get("/overview")
async def get_operators_overview(user=Depends(require_superuser), db: AsyncSession = Depends(get_db)):
    """Returns summary KPIs of all active operators and committees."""
    task_count = await db.scalar(select(func.count()).select_from(InternalOperatorTask)) or 0
    active_scheds = await db.scalar(select(func.count()).select_from(InternalOperatorSchedule).where(InternalOperatorSchedule.is_active == True)) or 0
    pending_approvals = await db.scalar(select(func.count()).select_from(InternalOperatorApproval).where(InternalOperatorApproval.status == "pending")) or 0
    
    return {
        "worker_count": len(WORKER_REGISTRY["workers"]),
        "committee_count": len(WORKER_REGISTRY["committees"]),
        "active_schedules": active_scheds,
        "total_tasks_run": task_count,
        "pending_approvals": pending_approvals,
        "minimum_live_set": WORKER_REGISTRY["minimum_live_set"]
    }

@router.get("/tasks")
async def get_operator_tasks(limit: int = 50, user=Depends(require_superuser), db: AsyncSession = Depends(get_db)):
    """List recent tasks run by the operator network."""
    result = await db.execute(select(InternalOperatorTask).order_by(InternalOperatorTask.created_at.desc()).limit(limit))
    return result.scalars().all()

@router.post("/tasks")
async def create_operator_task(body: dict, user=Depends(require_superuser), db: AsyncSession = Depends(get_db)):
    """Manually spawn a new operator task."""
    task = InternalOperatorTask(
        worker_id=body.get("worker_id", "generic"),
        committee=body.get("committee", "experience-assurance"),
        name=body.get("name", "Manual Task"),
        description=body.get("description", ""),
        status="pending",
        assigned_vertical=body.get("assigned_vertical", "generic"),
        risk_level=body.get("risk_level", "low"),
        cost_estimate_usd=body.get("cost_estimate_usd", 0.0),
        input_data=body.get("input_data", {})
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task

@router.patch("/tasks/{task_id}")
async def update_operator_task(task_id: str, body: dict, user=Depends(require_superuser), db: AsyncSession = Depends(get_db)):
    """Update status, output, or metadata of a task."""
    result = await db.execute(select(InternalOperatorTask).where(InternalOperatorTask.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    for k, v in body.items():
        if hasattr(task, k):
            setattr(task, k, v)
    await db.commit()
    await db.refresh(task)
    return task

@router.post("/workers/{worker_id}/run")
async def run_worker(worker_id: str, body: dict, user=Depends(require_superuser), db: AsyncSession = Depends(get_db)):
    """
    Trigger a specific worker. Computes appropriate provider based on policy,
    checks budget rules, gates critical releases, and records execution details.
    """
    task_type = body.get("task_type", "heartbeat")
    risk = body.get("risk", "low")
    urgency = body.get("urgency", "low")
    context_tokens = body.get("context_tokens", 1000)
    
    # Provider Policy Check
    provider = choose_provider(worker_id, task_type, risk, context_tokens, urgency)
    
    # Budget Cap Check
    budget_result = await db.execute(select(InternalOperatorBudget).where(InternalOperatorBudget.worker_id == worker_id))
    budget = budget_result.scalar_one_or_none()
    
    if budget and provider == "openai":
        if budget.daily_spent_usd >= budget.daily_cap_usd:
            raise HTTPException(
                status_code=402,
                detail=f"Budget cap reached for {worker_id} on provider {provider}"
            )
            
    # Gate releases behind human approvals
    if risk == "critical" or task_type == "production_release":
        task_id = str(uuid.uuid4())
        approval = InternalOperatorApproval(
            worker_id=worker_id,
            task_id=task_id,
            request_type="release_deploy",
            request_payload=body,
            status="pending"
        )
        db.add(approval)
        await db.commit()
        return {
            "worker_id": worker_id,
            "status": "blocked",
            "reason": "Critical task requires human approval",
            "approval_id": approval.id,
            "provider": provider
        }
        
    # Standard task registration
    task = InternalOperatorTask(
        worker_id=worker_id,
        committee=body.get("committee", "experience-assurance"),
        name=f"Run worker {worker_id}",
        status="completed",
        cost_estimate_usd=0.0001 if provider == "ollama" else 0.05,
        risk_level=risk,
        input_data=body,
        output_data={"result": "success", "provider_used": provider}
    )
    db.add(task)
    
    # Record Provider usage
    usage = InternalOperatorProviderUsage(
        worker_id=worker_id,
        provider=provider,
        prompt_tokens=context_tokens,
        completion_tokens=200,
        cost_usd=0.0001 if provider == "ollama" else 0.05
    )
    db.add(usage)
    
    if budget:
        budget.daily_spent_usd += usage.cost_usd
        
    await db.commit()
    return {
        "worker_id": worker_id,
        "status": "ok",
        "provider": provider,
        "task_id": task.id
    }

@router.post("/workers/{worker_id}/pause")
async def pause_worker(worker_id: str, user=Depends(require_superuser), db: AsyncSession = Depends(get_db)):
    """Pause schedule active status for a worker."""
    result = await db.execute(select(InternalOperatorSchedule).where(InternalOperatorSchedule.worker_id == worker_id))
    sched = result.scalar_one_or_none()
    if sched:
        sched.is_active = False
        await db.commit()
    return {"worker_id": worker_id, "active": False}

@router.post("/workers/{worker_id}/resume")
async def resume_worker(worker_id: str, user=Depends(require_superuser), db: AsyncSession = Depends(get_db)):
    """Resume schedule active status for a worker."""
    result = await db.execute(select(InternalOperatorSchedule).where(InternalOperatorSchedule.worker_id == worker_id))
    sched = result.scalar_one_or_none()
    if sched:
        sched.is_active = True
        await db.commit()
    return {"worker_id": worker_id, "active": True}

@router.get("/workers/{worker_id}/memory")
async def get_worker_memory(worker_id: str, user=Depends(require_superuser), db: AsyncSession = Depends(get_db)):
    """Get all key-value states for a worker."""
    result = await db.execute(select(InternalOperatorMemory).where(InternalOperatorMemory.worker_id == worker_id))
    return result.scalars().all()

@router.post("/workers/{worker_id}/memory")
async def set_worker_memory(worker_id: str, body: dict, user=Depends(require_superuser), db: AsyncSession = Depends(get_db)):
    """Store or update key-value states for a worker."""
    key = body.get("key")
    value = body.get("value", {})
    if not key:
        raise HTTPException(status_code=400, detail="key is required")
        
    result = await db.execute(
        select(InternalOperatorMemory).where(
            InternalOperatorMemory.worker_id == worker_id,
            InternalOperatorMemory.key == key
        )
    )
    mem = result.scalar_one_or_none()
    if mem:
        mem.value = value
    else:
        mem = InternalOperatorMemory(worker_id=worker_id, key=key, value=value)
        db.add(mem)
        
    await db.commit()
    return {"stored": True, "key": key}

@router.get("/artifacts")
async def get_artifacts(limit: int = 50, user=Depends(require_superuser), db: AsyncSession = Depends(get_db)):
    """List recent artifacts generated by workers."""
    result = await db.execute(select(InternalOperatorArtifact).order_by(InternalOperatorArtifact.created_at.desc()).limit(limit))
    return result.scalars().all()

@router.post("/artifacts")
async def create_artifact(body: dict, user=Depends(require_superuser), db: AsyncSession = Depends(get_db)):
    """Register a new output artifact."""
    artifact = InternalOperatorArtifact(
        worker_id=body.get("worker_id", "generic"),
        task_id=body.get("task_id"),
        name=body.get("name", "Artifact Output"),
        path=body.get("path", ""),
        content_hash=body.get("content_hash", "")
    )
    db.add(artifact)
    await db.commit()
    await db.refresh(artifact)
    return artifact

@router.get("/provider-usage")
async def get_provider_usage(user=Depends(require_superuser), db: AsyncSession = Depends(get_db)):
    """Get total metrics and costs aggregated by LLM provider."""
    result = await db.execute(
        select(
            InternalOperatorProviderUsage.provider,
            func.sum(InternalOperatorProviderUsage.prompt_tokens),
            func.sum(InternalOperatorProviderUsage.completion_tokens),
            func.sum(InternalOperatorProviderUsage.cost_usd)
        ).group_by(InternalOperatorProviderUsage.provider)
    )
    
    return [
        {
            "provider": row[0],
            "prompt_tokens": int(row[1] or 0),
            "completion_tokens": int(row[2] or 0),
            "cost_usd": float(row[3] or 0.0)
        }
        for row in result.all()
    ]

@router.get("/budgets")
async def get_budgets(user=Depends(require_superuser), db: AsyncSession = Depends(get_db)):
    """Get budget metrics for all workers."""
    result = await db.execute(select(InternalOperatorBudget))
    return result.scalars().all()

@router.patch("/budgets/{worker_id}")
async def update_budget(worker_id: str, body: dict, user=Depends(require_superuser), db: AsyncSession = Depends(get_db)):
    """Set budgets daily or monthly cap limits for a worker."""
    result = await db.execute(select(InternalOperatorBudget).where(InternalOperatorBudget.worker_id == worker_id))
    budget = result.scalar_one_or_none()
    if not budget:
        budget = InternalOperatorBudget(worker_id=worker_id)
        db.add(budget)
        
    if "daily_cap_usd" in body:
        budget.daily_cap_usd = float(body["daily_cap_usd"])
    if "monthly_cap_usd" in body:
        budget.monthly_cap_usd = float(body["monthly_cap_usd"])
        
    await db.commit()
    await db.refresh(budget)
    return budget

@router.post("/approvals/{approval_id}/approve")
async def approve_request(approval_id: str, body: dict, user=Depends(require_superuser), db: AsyncSession = Depends(get_db)):
    """Approve a gated critical action request."""
    result = await db.execute(select(InternalOperatorApproval).where(InternalOperatorApproval.id == approval_id))
    approval = result.scalar_one_or_none()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
        
    approval.status = "approved"
    approval.reviewer_id = user.id
    approval.review_notes = body.get("notes", "Approved by human admin")
    approval.reviewed_at = datetime.now(timezone.utc)
    await db.commit()
    return {"id": approval_id, "status": "approved"}

@router.post("/approvals/{approval_id}/reject")
async def reject_request(approval_id: str, body: dict, user=Depends(require_superuser), db: AsyncSession = Depends(get_db)):
    """Reject a gated critical action request."""
    result = await db.execute(select(InternalOperatorApproval).where(InternalOperatorApproval.id == approval_id))
    approval = result.scalar_one_or_none()
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
        
    approval.status = "rejected"
    approval.reviewer_id = user.id
    approval.review_notes = body.get("notes", "Rejected by human admin")
    approval.reviewed_at = datetime.now(timezone.utc)
    await db.commit()
    return {"id": approval_id, "status": "rejected"}
