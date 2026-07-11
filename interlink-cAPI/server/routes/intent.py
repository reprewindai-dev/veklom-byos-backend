"""POST /capi/intent — evaluate ExecutionIntent."""

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from typing import Dict, Any, Optional
import uuid
from ..core import pgl, policy, budget, evidence

router = APIRouter(tags=["intent"])

class ExecutionIntent(BaseModel):
    agent_id: str
    pgl_id: str
    target_resource: str
    action: str
    arguments: Dict[str, Any]
    context: Dict[str, Any]

@router.post("/intent")
async def evaluate_intent(
    intent: ExecutionIntent,
    x_capi_intent: Optional[str] = Header(None)
):
    """
    Evaluates an agent's execution intent through the 9-phase PGL gate.
    """
    # 1. PGL Certificate Validation
    cert_valid = await pgl.validate_certificate(intent.pgl_id)
    if not cert_valid:
        raise HTTPException(status_code=403, detail="Invalid or revoked PGL certificate")

    # 2. Policy Check
    verdict = await policy.evaluate(intent)
    if not verdict.allowed:
        # Create evidence of denial
        receipt_id = await evidence.seal_denial(intent, verdict.reason)
        return {"status": "denied", "reason": verdict.reason, "receipt_id": receipt_id}

    # 3. Budget Check
    budget_ok = await budget.check_and_reserve(intent.agent_id, intent.target_resource)
    if not budget_ok:
         return {"status": "denied", "reason": "Insufficient budget or cap reached"}

    # 4. Success — Return intent token or receipt
    receipt_id = await evidence.seal_intent(intent)

    return {
        "status": "approved",
        "intent_token": f"itk_{uuid.uuid4().hex[:12]}",
        "receipt_id": receipt_id
    }
