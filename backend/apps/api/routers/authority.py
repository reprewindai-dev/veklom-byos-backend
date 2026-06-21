"""Authority routes for Veklom Runtime Authority Pack."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database.database import get_db
from backend.core.security.auth import get_current_user, require_workspace_access, check_workspace_access
from backend.db.models.user import User
from backend.apps.api.services.authority import AuthorityService
from backend.apps.authority.api.seked import router as seked_router

router = APIRouter(prefix="/authority", tags=["Authority"])

# Include SEKED endpoints
router.include_router(seked_router)


@router.get("/context")
async def get_authority_context(
    agent_id: Optional[str] = Query(None, description="Agent ID to get context for"),
    workspace_id: Optional[str] = Query(None, description="Workspace ID to get context for"),
    authority_run_id: Optional[str] = Query(None, description="Authority run ID to get context for"),
    current_user: User = Depends(require_workspace_access),
    db: AsyncSession = Depends(get_db)
):
    """
    Get aggregated authority context for an agent, workspace, or authority run.
    
    Exactly one of agent_id, workspace_id, or authority_run_id must be provided.
    
    Returns comprehensive authority information including:
    - Agent info and birth certificate
    - Lineage information
    - Authority bundle and permissions
    - Active run and recent decisions
    - Risk assessment
    """
    
    # Validate that exactly one parameter is provided
    provided_params = [p for p in [agent_id, workspace_id, authority_run_id] if p is not None]
    if len(provided_params) != 1:
        raise HTTPException(
            status_code=400,
            detail="Exactly one of agent_id, workspace_id, or authority_run_id must be provided"
        )
    
    # Create authority service
    authority_service = AuthorityService(db)
    
    try:
        # Build authority context
        context = await authority_service.get_authority_context(
            agent_id=agent_id,
            workspace_id=workspace_id,
            authority_run_id=authority_run_id
        )
        
        return context.to_dict()
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        error_detail = f"Error building authority context: {str(e)}\nTraceback: {traceback.format_exc()}"
        print(error_detail)
        raise HTTPException(status_code=500, detail="Failed to build authority context")


@router.get("/bundles")
async def list_authority_bundles(
    workspace_id: Optional[str] = Query(None, description="Filter by workspace ID"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    current_user: User = Depends(require_workspace_access),
    db: AsyncSession = Depends(get_db)
):
    """List authority bundles accessible to the current user."""
    
    from sqlalchemy import select
    from backend.db.models.authority import AuthorityBundle
    
    # Build query
    query = select(AuthorityBundle)
    
    # Filter by workspace if specified
    if workspace_id:
        query = query.where(AuthorityBundle.workspace_id == workspace_id)
    else:
        # Only show bundles from user's workspace
        query = query.where(AuthorityBundle.workspace_id == current_user.workspace_id)
    
    # Filter by active status if specified
    if is_active is not None:
        query = query.where(AuthorityBundle.is_active == is_active)
    
    # Execute query
    result = await db.execute(query.order_by(AuthorityBundle.created_at.desc()))
    bundles = result.scalars().all()
    
    return [
        {
            "id": bundle.id,
            "name": bundle.name,
            "version": bundle.version,
            "workspace_id": bundle.workspace_id,
            "risk_level": bundle.risk_level,
            "description": bundle.description,
            "tags": bundle.tags,
            "is_active": bundle.is_active,
            "created_at": bundle.created_at.isoformat() if bundle.created_at else None,
            "updated_at": bundle.updated_at.isoformat() if bundle.updated_at else None
        }
        for bundle in bundles
    ]


@router.get("/runs")
async def list_authority_runs(
    agent_id: Optional[str] = Query(None, description="Filter by agent ID"),
    workspace_id: Optional[str] = Query(None, description="Filter by workspace ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    current_user: User = Depends(require_workspace_access),
    db: AsyncSession = Depends(get_db)
):
    """List authority runs accessible to the current user."""
    
    from sqlalchemy import select
    from backend.db.models.authority import AuthorityRun
    
    # Build query
    query = select(AuthorityRun)
    
    # Filter by workspace
    if workspace_id:
        query = query.where(AuthorityRun.workspace_id == workspace_id)
    else:
        # Only show runs from user's workspace
        query = query.where(AuthorityRun.workspace_id == current_user.workspace_id)
    
    # Apply additional filters
    if agent_id:
        query = query.where(AuthorityRun.agent_id == agent_id)
    
    if status:
        query = query.where(AuthorityRun.status == status)
    
    # Apply pagination
    query = query.order_by(AuthorityRun.created_at.desc()).limit(limit).offset(offset)
    
    # Execute query
    result = await db.execute(query)
    runs = result.scalars().all()
    
    return [
        {
            "id": run.id,
            "authority_bundle_id": run.authority_bundle_id,
            "agent_id": run.agent_id,
            "workspace_id": run.workspace_id,
            "executor_id": run.executor_id,
            "status": run.status,
            "start_time": run.start_time.isoformat() if run.start_time else None,
            "end_time": run.end_time.isoformat() if run.end_time else None,
            "total_actions": run.total_actions,
            "approved_actions": run.approved_actions,
            "denied_actions": run.denied_actions,
            "violation_count": run.violation_count,
            "evidence_pack_id": run.evidence_pack_id,
            "created_at": run.created_at.isoformat() if run.created_at else None,
            "updated_at": run.updated_at.isoformat() if run.updated_at else None
        }
        for run in runs
    ]


@router.get("/runs/{run_id}/decisions")
async def get_authority_decisions(
    run_id: str,
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get authority decisions for a specific run."""
    
    from sqlalchemy import select
    from backend.db.models.authority import AuthorityRun, AuthorityDecision
    
    # Verify access to the run
    run_result = await db.execute(
        select(AuthorityRun).where(AuthorityRun.id == run_id)
    )
    run = run_result.scalar_one_or_none()
    
    if not run:
        raise HTTPException(status_code=404, detail="Authority run not found")
    
    if not check_workspace_access(current_user, run.workspace_id):
        raise HTTPException(status_code=403, detail="Access denied to authority run")
    
    # Get decisions
    decisions_result = await db.execute(
        select(AuthorityDecision)
        .where(AuthorityDecision.authority_run_id == run_id)
        .order_by(AuthorityDecision.decision_time.desc())
        .limit(limit)
        .offset(offset)
    )
    decisions = decisions_result.scalars().all()
    
    return [
        {
            "id": decision.id,
            "tool_name": decision.tool_name,
            "tool_parameters": decision.tool_parameters,
            "decision": decision.decision,
            "reason": decision.reason,
            "confidence_score": decision.confidence_score,
            "agent_context": decision.agent_context,
            "workspace_context": decision.workspace_context,
            "risk_assessment": decision.risk_assessment,
            "decision_time": decision.decision_time.isoformat() if decision.decision_time else None,
            "execution_time": decision.execution_time.isoformat() if decision.execution_time else None,
            "evidence_refs": decision.evidence_refs,
            "created_at": decision.created_at.isoformat() if decision.created_at else None
        }
        for decision in decisions
    ]
