from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict, Any

from backend.db.session import get_db
from backend.db.models.run import VeklomRun
from backend.services.orchestrator import RunOrchestrator
from backend.core.security.auth import get_current_user
from backend.db.models.user import User

router = APIRouter()

@router.post("/", response_model=Dict[str, Any])
async def create_run(
    intent: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Step 1: Capture intent and create the atomic VeklomRun.
    """
    orchestrator = RunOrchestrator(db)
    
    # In a real scenario, workspace_id comes from active context or user model
    workspace_id = current_user.workspace_id or "default_workspace"
    tenant_id = workspace_id
    
    run = await orchestrator.create_run(
        workspace_id=workspace_id,
        tenant_id=tenant_id,
        actor_id=current_user.id,
        intent=intent
    )
    
    return {"run_id": run.run_id, "status": run.status.value}


@router.get("/{run_id}", response_model=Dict[str, Any])
async def get_run(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Inspect a VeklomRun.
    """
    result = await db.execute(select(VeklomRun).where(VeklomRun.run_id == run_id))
    run = result.scalar_one_or_none()
    
    if not run:
        raise HTTPException(status_code=404, detail="VeklomRun not found")
        
    # Tenant boundary check
    if run.actor_id != current_user.id and run.workspace_id != current_user.workspace_id:
         raise HTTPException(status_code=403, detail="Not authorized to view this run")
         
    return {
        "run_id": run.run_id,
        "status": run.status.value,
        "intent": run.intent,
        "v2_plan": run.v2_plan,
        "v4_decision": run.v4_decision,
        "pgl_identity": run.pgl_identity,
        "created_at": run.created_at.isoformat()
    }


@router.post("/{run_id}/compile", response_model=Dict[str, Any])
async def compile_run(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Triggers the UACP v2 Compiler to bound the intent into a structured plan.
    Marketplace-facing compile service.
    """
    result = await db.execute(select(VeklomRun).where(VeklomRun.run_id == run_id))
    run = result.scalar_one_or_none()
    
    if not run:
        raise HTTPException(status_code=404, detail="VeklomRun not found")
        
    orchestrator = RunOrchestrator(db)
    run = await orchestrator.compile_run(run)
    
    return {
        "run_id": run.run_id,
        "status": run.status.value,
        "v2_plan": run.v2_plan
    }


@router.post("/{run_id}/contextualize", response_model=Dict[str, Any])
async def contextualize_run(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Triggers the UACP v3 Contextual Brain to enrich the plan with workspace memory and RAG embeddings.
    """
    result = await db.execute(select(VeklomRun).where(VeklomRun.run_id == run_id))
    run = result.scalar_one_or_none()
    
    if not run:
        raise HTTPException(status_code=404, detail="VeklomRun not found")
        
    orchestrator = RunOrchestrator(db)
    run = await orchestrator.contextualize_run(run)
    
    return {
        "run_id": run.run_id,
        "status": run.status.value,
        "v3_context": run.v3_context
    }


@router.post("/{run_id}/govern", response_model=Dict[str, Any])
async def govern_run(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Triggers the UACP v4 Decision Kernel to evaluate the contextualized plan.
    Will transition the run to APPROVED, HELD, or DENIED based on policy evaluation.
    """
    result = await db.execute(select(VeklomRun).where(VeklomRun.run_id == run_id))
    run = result.scalar_one_or_none()
    
    if not run:
        raise HTTPException(status_code=404, detail="VeklomRun not found")
        
    orchestrator = RunOrchestrator(db)
    run = await orchestrator.govern_run(run)
    
    return {
        "run_id": run.run_id,
        "status": run.status.value,
        "v4_decision": run.v4_decision,
        "seked_state": run.seked_state
    }


@router.post("/{run_id}/approve", response_model=Dict[str, Any])
async def approve_run(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Approve a HELD run.
    """
    result = await db.execute(select(VeklomRun).where(VeklomRun.run_id == run_id))
    run = result.scalar_one_or_none()
    
    if not run:
        raise HTTPException(status_code=404, detail="VeklomRun not found")
        
    orchestrator = RunOrchestrator(db)
    # Move from HELD to APPROVED. commit_run will move APPROVED -> COMMITTED
    from backend.db.models.run import VeklomRunStatus
    run = await orchestrator._update_state(run, VeklomRunStatus.APPROVED)
    
    return {"run_id": run.run_id, "status": run.status.value}


@router.post("/{run_id}/rollback", response_model=Dict[str, Any])
async def rollback_run(
    run_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Rollback a run, creating a lineage edge in PGL.
    """
    result = await db.execute(select(VeklomRun).where(VeklomRun.run_id == run_id))
    run = result.scalar_one_or_none()
    
    if not run:
        raise HTTPException(status_code=404, detail="VeklomRun not found")
        
    orchestrator = RunOrchestrator(db)
    run = await orchestrator.rollback_run(run)
    
    return {"run_id": run.run_id, "status": run.status.value}
