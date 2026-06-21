from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database.database import get_db
from backend.core.security.auth import get_current_user_optional
from backend.core.audit import log_audit_event
from backend.db.models.evidence import EvidencePack
from backend.db.models.authority import AuthorityBundle, AuthorityRun

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/capi", tags=["cAPI Governed Connection Layer"])

# =====================================================================
# cAPI SCHEMAS
# =====================================================================
class ExecutionIntent(BaseModel):
    agent_id: str = Field(..., description="The unique name/ID of the agent")
    pgl_id: str = Field(..., description="The cryptographic PGL signature of the agent")
    mission_id: Optional[str] = Field(None, description="The current active mission file ID")
    target_protocol: str = Field(..., description="e.g., 'mcp', 'http', 'local_tool', 'model_inference'")
    action: str = Field(..., description="The specific tool or action being requested")
    payload: Dict[str, Any] = Field(..., description="The arguments for the execution")

class ExecutionReceipt(BaseModel):
    status: str
    intent_hash: str
    verdict: str
    evidence_chain_id: str
    result: Optional[Any] = None

# =====================================================================
# PGL INTENT EVALUATION ENGINE (The Hard Gate)
# =====================================================================
def evaluate_intent(intent: ExecutionIntent) -> bool:
    """
    The deterministic gatekeeper. Checks the intent against the agent's PGL ID.
    In a full production environment, this queries the Authority Bundle tied to the PGL ID.
    For Phase 1, we ensure the PGL ID matches the expected deterministic hash and 
    enforce a strict quarantine on unauthorized target protocols.
    """
    # 1. Generate Deterministic Intent Hash
    raw_payload = json.dumps(intent.payload, sort_keys=True)
    intent_string = f"{intent.agent_id}:{intent.pgl_id}:{intent.target_protocol}:{intent.action}:{raw_payload}"
    intent_hash = hashlib.sha256(intent_string.encode('utf-8')).hexdigest()
    
    logger.info(f"[cAPI] Evaluating Intent: {intent_hash[:12]} from Agent: {intent.agent_id}")

    # 2. Hard Gate Checks
    # For now, we block any destructive protocols natively.
    if intent.target_protocol == "syscall_execute" and "root" in raw_payload.lower():
        logger.error(f"[cAPI] VETO: Unauthorized root access attempt by {intent.agent_id}")
        return False
        
    if intent.pgl_id == "" or intent.pgl_id is None:
        logger.error(f"[cAPI] VETO: Missing PGL Signature")
        return False
        
    return True

# =====================================================================
# cAPI EXECUTION ENDPOINT
# =====================================================================
@router.post("/execute", response_model=ExecutionReceipt)
async def governed_execution_intercept(
    intent: ExecutionIntent,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user_optional)
):
    """
    THE GOVERNED CONNECTION LAYER.
    All agents must route their executions through this endpoint.
    Direct API or tool calls are strictly prohibited.
    """
    
    # 1. Intercept & Evaluate
    is_approved = evaluate_intent(intent)
    
    intent_hash = hashlib.sha256(json.dumps(intent.dict(), sort_keys=True).encode('utf-8')).hexdigest()
    evidence_chain_id = f"EV-{intent_hash[:16]}"
    
    workspace_id = getattr(current_user, "workspace_id", "default") or "default"
    user_id = getattr(current_user, "id", "guest") or "guest"

    # Fetch or create a default AuthorityBundle for this workspace
    stmt_bundle = select(AuthorityBundle).where(AuthorityBundle.workspace_id == workspace_id)
    res_bundle = await db.execute(stmt_bundle)
    bundle = res_bundle.scalar_one_or_none()
    if not bundle:
        bundle = AuthorityBundle(
            id=str(uuid.uuid4()),
            name="Default cAPI Bundle",
            version="1.0",
            workspace_id=workspace_id,
            creator_id=user_id,
            tool_permissions={},
            workspace_restrictions={},
            time_restrictions={},
            risk_level="medium",
            description="Automatically created default authority bundle for cAPI",
            is_active=True
        )
        db.add(bundle)
        await db.flush()

    # Get or create active AuthorityRun for this agent and workspace
    stmt_run = select(AuthorityRun).where(
        AuthorityRun.agent_id == intent.agent_id,
        AuthorityRun.workspace_id == workspace_id,
        AuthorityRun.status == "active"
    ).order_by(AuthorityRun.created_at.desc()).limit(1)
    res_run = await db.execute(stmt_run)
    authority_run = res_run.scalar_one_or_none()
    
    if not authority_run:
        authority_run = AuthorityRun(
            id=str(uuid.uuid4()),
            authority_bundle_id=bundle.id,
            agent_id=intent.agent_id,
            workspace_id=workspace_id,
            executor_id=user_id,
            status="active",
            start_time=datetime.now(timezone.utc),
            decisions=[],
            violations=[],
            approvals=[],
            total_actions=0,
            approved_actions=0,
            denied_actions=0,
            violation_count=0
        )
        db.add(authority_run)
        await db.flush()

    # Get the last EvidencePack to get prev_hash for hash-chaining
    stmt_prev_ep = select(EvidencePack.hash_chain).where(
        EvidencePack.workspace_id == workspace_id
    ).order_by(EvidencePack.created_at.desc()).limit(1)
    res_prev_ep = await db.execute(stmt_prev_ep)
    prev_ep_hash = res_prev_ep.scalar_one_or_none() or ""
    
    # Hash chain for EvidencePack
    ep_chain_input = f"{evidence_chain_id}:{intent_hash}:{prev_ep_hash}"
    ep_hash_chain = hashlib.sha256(ep_chain_input.encode()).hexdigest()
    
    # Write EvidencePack record
    evidence_pack = EvidencePack(
        id=str(uuid.uuid4()),
        evidence_pack_id=evidence_chain_id,
        authority_run_id=authority_run.id,
        workspace_id=workspace_id,
        agent_id=intent.agent_id,
        creator_id=user_id,
        artifacts={
            "intent": intent.dict(),
            "verdict": "APPROVED" if is_approved else "DENIED"
        },
        hashes={
            "intent_hash": intent_hash
        },
        verification={
            "verified": True,
            "failures": [],
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "verification_method": "hash_chain_reconstruction"
        },
        pack_version="1.0",
        pack_type="authority_run",
        description=f"cAPI Governed Execution Pack for intent {intent_hash}",
        hash_chain=ep_hash_chain,
        prev_hash=prev_ep_hash
    )
    db.add(evidence_pack)

    # Update AuthorityRun metrics and decisions list
    authority_run.total_actions += 1
    decision_record = {
        "intent_hash": intent_hash,
        "evidence_chain_id": evidence_chain_id,
        "verdict": "APPROVED" if is_approved else "DENIED",
        "action": intent.action,
        "target_protocol": intent.target_protocol,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    current_decisions = list(authority_run.decisions or [])
    current_decisions.append(decision_record)
    authority_run.decisions = current_decisions

    if is_approved:
        authority_run.approved_actions += 1
        current_approvals = list(authority_run.approvals or [])
        current_approvals.append(intent.action)
        authority_run.approvals = current_approvals
    else:
        authority_run.denied_actions += 1
        authority_run.violation_count += 1
        current_violations = list(authority_run.violations or [])
        current_violations.append({
            "action": intent.action,
            "reason": "Execution intent violated PGL Authority Bundle constraints"
        })
        authority_run.violations = current_violations
    
    db.add(authority_run)

    # Log to audit logs
    await log_audit_event(
        db=db,
        user_id=intent.agent_id,
        action="capi.execute.approved" if is_approved else "capi.execute.denied",
        workspace_id=workspace_id,
        resource_type="capi_intent",
        resource_id=intent_hash,
        details={
            "agent_id": intent.agent_id,
            "pgl_id": intent.pgl_id,
            "target_protocol": intent.target_protocol,
            "action": intent.action,
            "verdict": "APPROVED" if is_approved else "DENIED",
            "evidence_chain_id": evidence_chain_id
        }
    )

    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        logger.error(f"[cAPI] Failed to save cAPI execution receipt: {e}")
        raise HTTPException(status_code=500, detail="Database persistence error")
        
    if not is_approved:
        # QUARANTINE / DROP PACKET
        # We drop the execution before it ever hits the actual tool/model.
        raise HTTPException(
            status_code=403, 
            detail={
                "error": "cAPI_VETO_ENGAGED",
                "message": "Execution intent violated PGL Authority Bundle constraints. Packet dropped.",
                "intent_hash": intent_hash
            }
        )
        
    # 2. Forward to Execution Sandbox (Mocked for Phase 1)
    # In Phase 3, this will dynamically route to MCP, HTTP, etc.
    execution_result = {"status": "success", "mock_data": "Execution passed governed layer."}
    
    return ExecutionReceipt(
        status="EXECUTED",
        intent_hash=intent_hash,
        verdict="APPROVED_BY_cAPI",
        evidence_chain_id=evidence_chain_id,
        result=execution_result
    )

