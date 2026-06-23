from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict, Any, List
import json

from backend.core.database.database import get_db
from backend.core.security.auth import get_current_user, require_workspace_access, check_workspace_access
from backend.db.models.user import User
from backend.db.models.authority import AuthorityRun, AuthorityDecision
from backend.db.models.agent import AgentMemory

router = APIRouter(prefix="/forensics", tags=["Forensics"])

@router.get("/replay", response_model=Dict[str, Any])
async def forensics_replay(
    run_id: str = Query(..., description="The AuthorityRun ID to replay"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    The 'Black Box' Flight Recorder API.
    Given an AuthorityRun ID, this reconstructs the exact state of the agent 
    prior to failure, packaging prompts, tool responses, token usage, and 
    risk assessments into a chronological JSON timeline.
    """
    
    # Verify access to the run
    run_result = await db.execute(
        select(AuthorityRun).where(AuthorityRun.id == run_id)
    )
    run = run_result.scalar_one_or_none()
    
    if not run:
        raise HTTPException(status_code=404, detail="Authority run not found")
        
    if not check_workspace_access(current_user, run.workspace_id):
        raise HTTPException(status_code=403, detail="Access denied to authority run")
        
    # Get all decisions for this run to build the timeline
    decisions_result = await db.execute(
        select(AuthorityDecision)
        .where(AuthorityDecision.authority_run_id == run_id)
        .order_by(AuthorityDecision.decision_time.asc())
    )
    decisions = decisions_result.scalars().all()
    
    # Get agent memory/context
    memory_result = await db.execute(
        select(AgentMemory)
        .where(AgentMemory.agent_id == run.agent_id)
        .order_by(AgentMemory.created_at.asc())
    )
    memories = memory_result.scalars().all()
    
    timeline = []
    
    for decision in decisions:
        timeline.append({
            "timestamp": decision.decision_time.isoformat() if decision.decision_time else None,
            "type": "SEKED_DECISION",
            "tool_name": decision.tool_name,
            "tool_parameters": decision.tool_parameters,
            "decision": decision.decision,
            "reason": decision.reason,
            "confidence_score": decision.confidence_score,
            "risk_assessment": decision.risk_assessment
        })
        
    for mem in memories:
        timeline.append({
            "timestamp": mem.created_at.isoformat() if mem.created_at else None,
            "type": "AGENT_MEMORY",
            "memory_key": mem.memory_key,
            "memory_value": mem.memory_value,
            "importance": mem.importance
        })
        
    # Sort the combined timeline chronologically
    timeline.sort(key=lambda x: x.get("timestamp", ""))
    
    return {
        "status": "success",
        "run_id": run_id,
        "agent_id": run.agent_id,
        "timeline": timeline,
        "meta": {
            "total_events": len(timeline),
            "run_status": run.status
        }
    }
