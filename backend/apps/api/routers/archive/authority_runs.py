"""Authority Run API endpoints for Veklom Runtime Authority Pack."""

import hashlib
import json
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from backend.core.database.database import get_db
from backend.core.security.auth import get_current_user
from backend.db.models.authority import AuthorityRun, AuthorityDecision, AuthorityBundle
from backend.db.models.user import User
from backend.core.services.seked_service import seked_service

router = APIRouter(prefix="/authority/runs", tags=["Authority Runs"])


@router.post("/", response_model=Dict[str, Any])
async def create_authority_run(
    authority_run_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new AuthorityRun for governed execution."""
    
    # Validate required fields
    required_fields = ["authority_bundle_id", "agent_id", "workspace_id", "executor_id"]
    for field in required_fields:
        if field not in authority_run_data:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required field: {field}"
            )
    
    # Verify authority bundle exists and belongs to workspace
    bundle_result = await db.execute(
        select(AuthorityBundle).where(
            and_(
                AuthorityBundle.id == authority_run_data["authority_bundle_id"],
                AuthorityBundle.workspace_id == current_user.workspace_id
            )
        )
    )
    bundle = bundle_result.scalar_one_or_none()
    
    if not bundle:
        raise HTTPException(
            status_code=404,
            detail="Authority bundle not found or access denied"
        )
    
    # Create AuthorityRun
    authority_run = AuthorityRun(
        authority_bundle_id=authority_run_data["authority_bundle_id"],
        agent_id=authority_run_data["agent_id"],
        workspace_id=authority_run_data["workspace_id"],
        executor_id=authority_run_data["executor_id"],
        status="active"
    )
    
    # Initialize with SEKED if measurement provided
    if "seked_measurement" in authority_run_data:
        seked_service.initialize_authority_run_with_seked(
            authority_run, 
            authority_run_data["seked_measurement"]
        )
    
    db.add(authority_run)
    await db.commit()
    await db.refresh(authority_run)
    
    return {
        "id": authority_run.id,
        "authority_bundle_id": authority_run.authority_bundle_id,
        "agent_id": authority_run.agent_id,
        "workspace_id": authority_run.workspace_id,
        "executor_id": authority_run.executor_id,
        "status": authority_run.status,
        "start_time": authority_run.start_time.isoformat(),
        "seked_initial_measurement": authority_run.seked_initial_measurement,
        "seked_final_directive": authority_run.seked_final_directive
    }


@router.get("/{run_id}/context", response_model=Dict[str, Any])
async def get_authority_context(
    run_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get AuthorityContext for a specific AuthorityRun."""
    
    result = await db.execute(
        select(AuthorityRun).where(
            and_(
                AuthorityRun.id == run_id,
                AuthorityRun.workspace_id == current_user.workspace_id
            )
        )
    )
    authority_run = result.scalar_one_or_none()
    
    if not authority_run:
        raise HTTPException(
            status_code=404,
            detail="Authority run not found"
        )
    
    # Get authority bundle
    bundle_result = await db.execute(
        select(AuthorityBundle).where(
            AuthorityBundle.id == authority_run.authority_bundle_id
        )
    )
    bundle = bundle_result.scalar_one_or_none()
    
    # Get latest decision
    decision_result = await db.execute(
        select(AuthorityDecision).where(
            AuthorityDecision.authority_run_id == run_id
        ).order_by(AuthorityDecision.decision_time.desc())
    )
    latest_decision = decision_result.scalar_one_or_none()
    
    return {
        "authority_run_id": authority_run.id,
        "authority_bundle": {
            "id": bundle.id if bundle else None,
            "name": bundle.name if bundle else None,
            "policy_version": bundle.policy_version if bundle else None,
            "constraints": bundle.constraints if bundle else {}
        },
        "agent_id": authority_run.agent_id,
        "workspace_id": authority_run.workspace_id,
        "executor_id": authority_run.executor_id,
        "status": authority_run.status,
        "seked_measurement": {
            "initial": authority_run.seked_initial_measurement,
            "final": authority_run.seked_final_directive
        },
        "latest_decision": {
            "id": latest_decision.id if latest_decision else None,
            "decision": latest_decision.decision if latest_decision else None,
            "reason": latest_decision.reason if latest_decision else None,
            "decision_time": latest_decision.decision_time.isoformat() if latest_decision else None
        },
        "execution_identity": {
            "id": f"exec_{authority_run.id[:8]}",
            "status": "active" if authority_run.status == "active" else "completed",
            "scope": latest_decision.tool_name if latest_decision else None,
            "expires_at": (authority_run.start_time + timedelta(hours=24)).isoformat()
        },
        "created_at": authority_run.start_time.isoformat(),
        "updated_at": authority_run.updated_at.isoformat() if authority_run.updated_at else None
    }


@router.get("/{run_id}/evidence", response_model=Dict[str, Any])
async def get_authority_evidence(
    run_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get EvidencePack for a specific AuthorityRun."""
    
    result = await db.execute(
        select(AuthorityRun).where(
            and_(
                AuthorityRun.id == run_id,
                AuthorityRun.workspace_id == current_user.workspace_id
            )
        )
    )
    authority_run = result.scalar_one_or_none()
    
    if not authority_run:
        raise HTTPException(
            status_code=404,
            detail="Authority run not found"
        )
    
    # Get all decisions for this run
    decisions_result = await db.execute(
        select(AuthorityDecision).where(
            AuthorityDecision.authority_run_id == run_id
        ).order_by(AuthorityDecision.decision_time.asc())
    )
    decisions = decisions_result.scalars().all()
    
    # Generate evidence hash chain
    evidence_items = []
    previous_hash = None
    
    for decision in decisions:
        evidence_data = {
            "decision_id": decision.id,
            "tool_name": decision.tool_name,
            "decision": decision.decision,
            "reason": decision.reason,
            "decision_time": decision.decision_time.isoformat(),
            "previous_hash": previous_hash
        }
        
        # Simple hash for demonstration (use proper crypto in production)
        current_hash = hashlib.sha256(
            json.dumps(evidence_data, sort_keys=True).encode()
        ).hexdigest()
        
        evidence_data["hash"] = current_hash
        evidence_items.append(evidence_data)
        previous_hash = current_hash
    
    return {
        "evidence_pack_id": f"evidence_{run_id}",
        "authority_run_id": run_id,
        "evidence_chain": evidence_items,
        "chain_root_hash": previous_hash,
        "total_decisions": len(decisions),
        "created_at": authority_run.start_time.isoformat(),
        "generated_at": datetime.now(timezone.utc).isoformat()
    }


@router.get("/{run_id}", response_model=Dict[str, Any])
async def get_authority_run(
    run_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific AuthorityRun."""
    
    result = await db.execute(
        select(AuthorityRun).where(
            and_(
                AuthorityRun.id == run_id,
                AuthorityRun.workspace_id == current_user.workspace_id
            )
        )
    )
    authority_run = result.scalar_one_or_none()
    
    if not authority_run:
        raise HTTPException(
            status_code=404,
            detail="Authority run not found"
        )
    
    # Get decisions for this run
    decisions_result = await db.execute(
        select(AuthorityDecision).where(
            AuthorityDecision.authority_run_id == run_id
        ).order_by(AuthorityDecision.decision_time.desc())
    )
    decisions = decisions_result.scalars().all()
    
    return {
        "id": authority_run.id,
        "authority_bundle_id": authority_run.authority_bundle_id,
        "agent_id": authority_run.agent_id,
        "workspace_id": authority_run.workspace_id,
        "executor_id": authority_run.executor_id,
        "status": authority_run.status,
        "start_time": authority_run.start_time.isoformat(),
        "end_time": authority_run.end_time.isoformat() if authority_run.end_time else None,
        "decisions": [
            {
                "id": d.id,
                "tool_name": d.tool_name,
                "decision": d.decision,
                "reason": d.reason,
                "confidence_score": d.confidence_score,
                "seked_measurement": d.seked_measurement,
                "seked_ratios": d.seked_ratios,
                "seked_directive": d.seked_directive,
                "decision_time": d.decision_time.isoformat(),
                "execution_time": d.execution_time.isoformat() if d.execution_time else None
            }
            for d in decisions
        ],
        "metrics": {
            "total_actions": authority_run.total_actions,
            "approved_actions": authority_run.approved_actions,
            "denied_actions": authority_run.denied_actions,
            "violation_count": authority_run.violation_count
        },
        "seked_initial_measurement": authority_run.seked_initial_measurement,
        "seked_final_directive": authority_run.seked_final_directive,
        "evidence_pack_id": authority_run.evidence_pack_id
    }


@router.get("/{run_id}/context", response_model=Dict[str, Any])
async def get_authority_context(
    run_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get comprehensive authority context for a run."""
    
    # Get authority run
    run_result = await db.execute(
        select(AuthorityRun).where(
            and_(
                AuthorityRun.id == run_id,
                AuthorityRun.workspace_id == current_user.workspace_id
            )
        )
    )
    authority_run = run_result.scalar_one_or_none()
    
    if not authority_run:
        raise HTTPException(
            status_code=404,
            detail="Authority run not found"
        )
    
    # Get authority bundle
    bundle_result = await db.execute(
        select(AuthorityBundle).where(
            AuthorityBundle.id == authority_run.authority_bundle_id
        )
    )
    bundle = bundle_result.scalar_one_or_none()
    
    # Get latest decision with SEKED data
    latest_decision_result = await db.execute(
        select(AuthorityDecision).where(
            AuthorityDecision.authority_run_id == run_id
        ).order_by(AuthorityDecision.decision_time.desc()).limit(1)
    )
    latest_decision = latest_decision_result.scalar_one_or_none()
    
    context = {
        "authority_run": {
            "id": authority_run.id,
            "status": authority_run.status,
            "start_time": authority_run.start_time.isoformat(),
            "end_time": authority_run.end_time.isoformat() if authority_run.end_time else None,
            "seked_initial_measurement": authority_run.seked_initial_measurement,
            "seked_final_directive": authority_run.seked_final_directive
        },
        "authority_bundle": {
            "id": bundle.id if bundle else None,
            "name": bundle.name if bundle else None,
            "risk_level": bundle.risk_level if bundle else None,
            "tool_permissions": bundle.tool_permissions if bundle else None,
            "workspace_restrictions": bundle.workspace_restrictions if bundle else None
        },
        "seked_state": None,
        "metrics": {
            "total_actions": authority_run.total_actions,
            "approved_actions": authority_run.approved_actions,
            "denied_actions": authority_run.denied_actions,
            "violation_count": authority_run.violation_count
        }
    }
    
    # Add SEKED state if available
    if latest_decision and latest_decision.seked_measurement:
        context["seked_state"] = {
            "measurement": latest_decision.seked_measurement,
            "ratios": latest_decision.seked_ratios,
            "directive": latest_decision.seked_directive,
            "timestamp": latest_decision.decision_time.isoformat()
        }
    
    return context


@router.get("/{run_id}/evidence", response_model=Dict[str, Any])
async def get_authority_evidence(
    run_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get evidence pack for an authority run."""
    
    # Verify authority run exists and user has access
    run_result = await db.execute(
        select(AuthorityRun).where(
            and_(
                AuthorityRun.id == run_id,
                AuthorityRun.workspace_id == current_user.workspace_id
            )
        )
    )
    authority_run = run_result.scalar_one_or_none()
    
    if not authority_run:
        raise HTTPException(
            status_code=404,
            detail="Authority run not found"
        )
    
    # Get all decisions for evidence
    decisions_result = await db.execute(
        select(AuthorityDecision).where(
            AuthorityDecision.authority_run_id == run_id
        ).order_by(AuthorityDecision.decision_time.asc())
    )
    decisions = decisions_result.scalars().all()
    
    evidence_pack = {
        "run_id": run_id,
        "authority_run_id": authority_run.id,
        "workspace_id": authority_run.workspace_id,
        "agent_id": authority_run.agent_id,
        "bundle_id": authority_run.authority_bundle_id,
        "created_at": authority_run.start_time.isoformat(),
        "completed_at": authority_run.end_time.isoformat() if authority_run.end_time else None,
        "status": authority_run.status,
        "decisions": [
            {
                "id": d.id,
                "tool_name": d.tool_name,
                "tool_parameters": d.tool_parameters,
                "decision": d.decision,
                "reason": d.reason,
                "confidence_score": d.confidence_score,
                "seked_measurement": d.seked_measurement,
                "seked_ratios": d.seked_ratios,
                "seked_directive": d.seked_directive,
                "seked_policy_id": d.seked_policy_id,
                "seked_proof_id": d.seked_proof_id,
                "agent_context": d.agent_context,
                "workspace_context": d.workspace_context,
                "risk_assessment": d.risk_assessment,
                "decision_time": d.decision_time.isoformat(),
                "execution_time": d.execution_time.isoformat() if d.execution_time else None,
                "evidence_refs": d.evidence_refs,
                "hash_chain": d.hash_chain
            }
            for d in decisions
        ],
        "metrics": {
            "total_actions": authority_run.total_actions,
            "approved_actions": authority_run.approved_actions,
            "denied_actions": authority_run.denied_actions,
            "violation_count": authority_run.violation_count
        },
        "seked_summary": {
            "initial_measurement": authority_run.seked_initial_measurement,
            "final_directive": authority_run.seked_final_directive
        },
        "audit_hash": authority_run.hash_chain,
        "evidence_pack_id": authority_run.evidence_pack_id
    }
    
    return evidence_pack


@router.post("/{run_id}/decisions", response_model=Dict[str, Any])
async def create_authority_decision(
    run_id: str,
    decision_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new authority decision within a run."""
    
    # Verify authority run exists and user has access
    run_result = await db.execute(
        select(AuthorityRun).where(
            and_(
                AuthorityRun.id == run_id,
                AuthorityRun.workspace_id == current_user.workspace_id
            )
        )
    )
    authority_run = run_result.scalar_one_or_none()
    
    if not authority_run:
        raise HTTPException(
            status_code=404,
            detail="Authority run not found"
        )
    
    # Validate required fields
    required_fields = ["tool_name", "tool_parameters"]
    for field in required_fields:
        if field not in decision_data:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required field: {field}"
            )
    
    # Create authority decision
    authority_decision = AuthorityDecision(
        authority_run_id=run_id,
        tool_name=decision_data["tool_name"],
        tool_parameters=decision_data["tool_parameters"],
        decision="approve",  # Will be updated by SEKED
        agent_context=decision_data.get("agent_context", {}),
        workspace_context=decision_data.get("workspace_context", {}),
        risk_assessment=decision_data.get("risk_assessment", {})
    )
    
    # Apply SEKED decision if measurement provided
    seked_measurement = decision_data.get("seked_measurement")
    if seked_measurement:
        seked_service.apply_seked_decision(authority_decision, seked_measurement)
    
    # Update run metrics
    if authority_decision.decision == "approve":
        authority_run.approved_actions += 1
    elif authority_decision.decision == "deny":
        authority_run.denied_actions += 1
    
    authority_run.total_actions += 1
    
    db.add(authority_decision)
    await db.commit()
    await db.refresh(authority_decision)
    
    return {
        "id": authority_decision.id,
        "authority_run_id": authority_decision.authority_run_id,
        "tool_name": authority_decision.tool_name,
        "decision": authority_decision.decision,
        "reason": authority_decision.reason,
        "confidence_score": authority_decision.confidence_score,
        "seked_measurement": authority_decision.seked_measurement,
        "seked_ratios": authority_decision.seked_ratios,
        "seked_directive": authority_decision.seked_directive,
        "decision_time": authority_decision.decision_time.isoformat()
    }


@router.put("/{run_id}/status", response_model=Dict[str, Any])
async def update_authority_run_status(
    run_id: str,
    status_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update authority run status."""
    
    # Verify authority run exists and user has access
    run_result = await db.execute(
        select(AuthorityRun).where(
            and_(
                AuthorityRun.id == run_id,
                AuthorityRun.workspace_id == current_user.workspace_id
            )
        )
    )
    authority_run = run_result.scalar_one_or_none()
    
    if not authority_run:
        raise HTTPException(
            status_code=404,
            detail="Authority run not found"
        )
    
    # Validate status
    new_status = status_data.get("status")
    valid_statuses = ["active", "completed", "failed", "revoked"]
    
    if new_status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {valid_statuses}"
        )
    
    # Update status
    authority_run.status = new_status
    
    if new_status in ["completed", "failed", "revoked"]:
        authority_run.end_time = datetime.now(timezone.utc)
    
    await db.commit()
    await db.refresh(authority_run)
    
    return {
        "id": authority_run.id,
        "status": authority_run.status,
        "start_time": authority_run.start_time.isoformat(),
        "end_time": authority_run.end_time.isoformat() if authority_run.end_time else None
    }
