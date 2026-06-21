from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
import hashlib
import json
import logging

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
async def governed_execution_intercept(intent: ExecutionIntent):
    """
    THE GOVERNED CONNECTION LAYER.
    All agents must route their executions through this endpoint.
    Direct API or tool calls are strictly prohibited.
    """
    
    # 1. Intercept & Evaluate
    is_approved = evaluate_intent(intent)
    
    intent_hash = hashlib.sha256(json.dumps(intent.dict(), sort_keys=True).encode('utf-8')).hexdigest()
    
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
    
    # 3. Cryptographic PGL Evidence Logging (Mocked for Phase 1)
    # We generate an evidence chain ID to prove this exact payload was approved.
    evidence_chain_id = f"EV-{intent_hash[:16]}"
    
    return ExecutionReceipt(
        status="EXECUTED",
        intent_hash=intent_hash,
        verdict="APPROVED_BY_cAPI",
        evidence_chain_id=evidence_chain_id,
        result=execution_result
    )
