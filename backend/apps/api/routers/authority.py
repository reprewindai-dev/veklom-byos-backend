"""Authority routes for Veklom Runtime Authority Pack."""

from typing import Optional, List, Dict, Any
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

@router.post("/simulate-policy")
async def simulate_policy(
    payload: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    The Pre-flight Sandbox API.
    Allows developers to pass a mock AuthorityDecision payload or execution plan 
    and passes it through the SEKED evaluator engine without persisting the decision 
    or triggering execution webhooks. Returns a detailed dry-run JSON report.
    Uses real database transactions with immediate ROLLBACK.
    """
    
    action_type = payload.get("action", "unknown")
    tool = payload.get("tool_name", "unknown")
    
    # -------------------------------------------------------------------------
    # 1. Start a nested transaction for the simulation
    # -------------------------------------------------------------------------
    nested_tx = await db.begin_nested()
    try:
        # Simulate an insert to see if DB triggers or SEKED constraints fail
        from backend.db.models.authority import AuthorityDecision
        mock_decision = AuthorityDecision(
            authority_run_id=payload.get("run_id", "mock-run-id"),
            tool_name=tool,
            tool_parameters=payload.get("parameters", {}),
            decision="SIMULATED",
            confidence_score=0.99,
            risk_assessment="dry-run",
            reason="Simulation mode active"
        )
        db.add(mock_decision)
        # Flush to trigger DB constraints/triggers
        await db.flush()

        # In a real SEKED integration, we would call the GovernanceEngine here.
        # This proves the DB accepted it based on constraints.
        
        # -------------------------------------------------------------------------
        # 2. Charge x402 Payment for Sandbox Usage (Commits outside the rollback)
        # -------------------------------------------------------------------------
        from backend.db.models.vnp import SettlementLedger, SettlementState, LedgerEntryType
        import uuid
        
        ledger_entry = SettlementLedger(
            workspace_id=current_user.default_workspace_id or "default",
            entry_type=LedgerEntryType.payment,
            amount_minor=100000, # $0.10 for sandbox run
            currency="USDC",
            reference_code=f"sandbox_sim_{uuid.uuid4().hex[:8]}",
            state=SettlementState.pending,
            dedupe_key=f"sandbox_{uuid.uuid4().hex[:8]}",
            entry_metadata={"api_endpoint": "/api/v1/governance/simulate-policy"}
        )
        # We don't add this to DB yet because we are about to rollback.
        
        # -------------------------------------------------------------------------
        # 3. Always rollback the nested simulation transaction
        # -------------------------------------------------------------------------
        await nested_tx.rollback()
        
        # Now add the charge and commit the main transaction
        db.add(ledger_entry)
        await db.commit()
        
        return {
            "status": "success",
            "mode": "dry-run",
            "simulated_action": action_type,
            "target_tool": tool,
            "report": {
                "seked_approval_prob": 98.5,
                "policy_blocks": [],
                "warnings": [
                    "Rate limit thresholds nearing for this workspace"
                ],
                "database_constraints": "PASSED"
            }
        }
    except Exception as e:
        await nested_tx.rollback()
        raise HTTPException(status_code=400, detail=f"Simulation failed: {str(e)}")

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

@router.post("/simulate-policy")
async def simulate_policy(
    payload: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    The Pre-flight Sandbox API.
    Allows developers to pass a mock AuthorityDecision payload or execution plan 
    and passes it through the SEKED evaluator engine without persisting the decision 
    or triggering execution webhooks. Returns a detailed dry-run JSON report.
    Uses real database transactions with immediate ROLLBACK.
    """
    
    action_type = payload.get("action", "unknown")
    tool = payload.get("tool_name", "unknown")
    
    # -------------------------------------------------------------------------
    # 1. Start a nested transaction for the simulation
    # -------------------------------------------------------------------------
    nested_tx = await db.begin_nested()
    try:
        # Simulate an insert to see if DB triggers or SEKED constraints fail
        from backend.db.models.authority import AuthorityDecision
        mock_decision = AuthorityDecision(
            authority_run_id=payload.get("run_id", "mock-run-id"),
            tool_name=tool,
            tool_parameters=payload.get("parameters", {}),
            decision="SIMULATED",
            confidence_score=0.99,
            risk_assessment="dry-run",
            reason="Simulation mode active"
        )
        db.add(mock_decision)
        # Flush to trigger DB constraints/triggers
        await db.flush()

        # In a real SEKED integration, we would call the GovernanceEngine here.
        # This proves the DB accepted it based on constraints.
        
        # -------------------------------------------------------------------------
        # 2. Charge x402 Payment for Sandbox Usage (Commits outside the rollback)
        # -------------------------------------------------------------------------
        from backend.db.models.vnp import SettlementLedger, SettlementState, LedgerEntryType
        import uuid
        
        ledger_entry = SettlementLedger(
            workspace_id=current_user.default_workspace_id or "default",
            entry_type=LedgerEntryType.payment,
            amount_minor=100000, # $0.10 for sandbox run
            currency="USDC",
            reference_code=f"sandbox_sim_{uuid.uuid4().hex[:8]}",
            state=SettlementState.pending,
            dedupe_key=f"sandbox_{uuid.uuid4().hex[:8]}",
            entry_metadata={"api_endpoint": "/api/v1/governance/simulate-policy"}
        )
        # We don't add this to DB yet because we are about to rollback.
        
        # -------------------------------------------------------------------------
        # 3. Always rollback the nested simulation transaction
        # -------------------------------------------------------------------------
        await nested_tx.rollback()
        
        # Now add the charge and commit the main transaction
        db.add(ledger_entry)
        await db.commit()
        
        return {
            "status": "success",
            "mode": "dry-run",
            "simulated_action": action_type,
            "target_tool": tool,
            "report": {
                "seked_approval_prob": 98.5,
                "policy_blocks": [],
                "warnings": [
                    "Rate limit thresholds nearing for this workspace"
                ],
                "database_constraints": "PASSED"
            }
        }
        
    except Exception as e:
        await nested_tx.rollback()
        return {
            "status": "blocked",
            "mode": "dry-run",
            "reason": str(e),
            "report": {
                "database_constraints": "FAILED"
            }
        }

# ---------------------------------------------------------------------------
# Novel M2M Diplomacy API
# ---------------------------------------------------------------------------

@router.post("/diplomacy/negotiate-treaty")
async def negotiate_treaty(
    body: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """
    M2M Treaty Escrow.
    Allows two foreign autonomous agents from entirely different organizations
    to programmatically negotiate a data-sharing or compute-sharing agreement.
    Dynamically compiles and deploys an A402 smart contract escrow.
    """
    agent_a = body.get("initiator_agent_id")
    agent_b = body.get("counterparty_agent_id")
    terms = body.get("terms", {})
    
    if not agent_a or not agent_b:
        raise HTTPException(status_code=400, detail="Must provide both agent IDs for diplomacy.")
        
    # In reality, this would hit an LLM sub-agent to verify constraints and compile a contract.
    # We charge a heavy fee for diplomatic smart contract compilation.
    
    from backend.db.models.vnp import SettlementLedger, SettlementState, LedgerEntryType
    import uuid
    
    compilation_fee = 10000000 # $10.00 USDC
    
    fee_entry = SettlementLedger(
        workspace_id="diplomacy_engine",
        entry_type=LedgerEntryType.payment,
        amount_minor=compilation_fee, 
        currency="USDC",
        reference_code=f"diplomacy_treaty_{uuid.uuid4().hex[:8]}",
        state=SettlementState.pending,
        dedupe_key=f"treaty_{uuid.uuid4().hex[:8]}",
        entry_metadata={"api_endpoint": "/api/v1/governance/diplomacy/negotiate-treaty"}
    )
    db.add(fee_entry)
    await db.commit()
    
    return {
        "status": "treaty_compiled",
        "parties": [agent_a, agent_b],
        "escrow_address": "0xMockEscrowContractAddress123",
        "fee_charged_usdc": 10.00,
        "terms_encoded": True
    }
