from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict, Any, Optional
from pydantic import BaseModel

from backend.core.database.database import get_db
from backend.db.models.run import VeklomRun
from backend.services.orchestrator import RunOrchestrator
from backend.core.security.auth import get_current_user
from backend.db.models.user import User

router = APIRouter()

class CreateRunResponse(BaseModel):
    run_id: str
    status: str

class GetRunResponse(BaseModel):
    run_id: str
    status: str
    intent: Optional[dict] = None
    v2_plan: Optional[dict] = None
    v4_decision: Optional[str] = None
    pgl_identity: Optional[str] = None
    created_at: str

class CompileRunResponse(BaseModel):
    run_id: str
    status: str
    v2_plan: Optional[dict] = None

class ContextualizeRunResponse(BaseModel):
    run_id: str
    status: str
    v3_context: Optional[dict] = None

class GovernRunResponse(BaseModel):
    run_id: str
    status: str
    v4_decision: Optional[str] = None
    seked_state: Optional[dict] = None

class ApproveRunResponse(BaseModel):
    run_id: str
    status: str

class RollbackRunResponse(BaseModel):
    run_id: str
    status: str

@router.post("/", response_model=CreateRunResponse)
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
    
    return CreateRunResponse(run_id=run.run_id, status=run.status.value)


@router.get("/{run_id}", response_model=GetRunResponse)
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
         
    return GetRunResponse(
        run_id=run.run_id,
        status=run.status.value,
        intent=run.intent,
        v2_plan=run.v2_plan,
        v4_decision=run.v4_decision,
        pgl_identity=run.pgl_identity,
        created_at=run.created_at.isoformat()
    )


@router.post("/{run_id}/compile", response_model=CompileRunResponse)
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
    
    return CompileRunResponse(
        run_id=run.run_id,
        status=run.status.value,
        v2_plan=run.v2_plan
    )


@router.post("/{run_id}/contextualize", response_model=ContextualizeRunResponse)
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
    
    return ContextualizeRunResponse(
        run_id=run.run_id,
        status=run.status.value,
        v3_context=run.v3_context
    )


@router.post("/{run_id}/govern", response_model=GovernRunResponse)
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
    
    return GovernRunResponse(
        run_id=run.run_id,
        status=run.status.value,
        v4_decision=run.v4_decision,
        seked_state=run.seked_state
    )


@router.post("/{run_id}/approve", response_model=ApproveRunResponse)
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
    
    return ApproveRunResponse(run_id=run.run_id, status=run.status.value)


@router.post("/{run_id}/rollback", response_model=RollbackRunResponse)
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
    
    return RollbackRunResponse(run_id=run.run_id, status=run.status.value)
