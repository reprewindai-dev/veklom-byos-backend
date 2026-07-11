"""GET /capi/governance — policy status + audit."""

from fastapi import APIRouter
from typing import List, Dict, Any
from ..core import policy, evidence

router = APIRouter(tags=["governance"])

@router.get("/governance/status")
async def get_policy_status():
    """Returns the current policy engine status and active rules."""
    return await policy.get_status()

@router.get("/governance/audit")
async def get_audit_trail(limit: int = 100):
    """Returns the recent audit trail of intent evaluations and receipts."""
    return await evidence.get_recent_audit(limit=limit)
