"""
VNP v2.0 Unified Execution Router.
Aligned with MCPAPI v2.0 and the Interlink Rust prototype.
"""

import uuid
import logging
import hashlib
import json
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database.database import get_db
from backend.core.vnp.models import (
    InvocationRequest, RuntimeResponse, RiskLevel, Capability, CapabilityContext, TransportType
)
from backend.core.vnp.enforcer import SafetyEnforcer, PolicyEngine, PolicyDecision
from backend.core.services.pgl_client import PGLClient
from backend.core.services.settlement_service import SettlementService
from backend.core.security.auth import get_current_user_or_api_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/vnp/v2", tags=["VNP v2.0"])

# Mock Registry for demonstration
MOCK_CAPABILITIES = [
    Capability(
        id="github.get_repo",
        title="Get Repository Details",
        description="Fetches metadata for a GitHub repository",
        tags=["github", "read"],
        risk=RiskLevel.Low,
        scopes=["repo:read"],
        input_schema={"type": "object", "properties": {"owner": {"type": "string"}, "repo": {"type": "string"}}, "required": ["owner", "repo"]},
        output_schema={"type": "object"},
        toolset="github"
    ),
    Capability(
        id="github.create_issue",
        title="Create Issue",
        description="Creates a new issue in a GitHub repository",
        tags=["github", "write"],
        risk=RiskLevel.Medium,
        scopes=["repo:write"],
        input_schema={"type": "object", "properties": {"owner": {"type": "string"}, "repo": {"type": "string"}, "title": {"type": "string"}}, "required": ["owner", "repo", "title"]},
        output_schema={"type": "object"},
        toolset="github"
    )
]

enforcer = SafetyEnforcer(MOCK_CAPABILITIES)
pgl_client = PGLClient()

async def execute_capability(
    db: AsyncSession,
    req: InvocationRequest,
    tenant_id: str
) -> RuntimeResponse:
    """The Unified Execution Core: Collapses logic paths."""

    # 1. Safety Plane
    cap, error = enforcer.validate_invocation(req)
    if error:
        # Seal evidence of violation
        pgl_res = await pgl_client.create_ledger_event(
            agent_id=req.context.actor_id,
            event_type="SafetyViolation",
            details={"request": req.model_dump(), "reason": error}
        )
        pgl_hash = pgl_res.get("event_hash", "unverified")
        return RuntimeResponse(type="SafetyViolation", reason=error, pgl_hash=pgl_hash)

    # 2. Policy Plane
    decision = PolicyEngine.evaluate(req, cap)

    if decision.decision == "Deny":
        pgl_res = await pgl_client.create_ledger_event(
            agent_id=req.context.actor_id,
            event_type="PolicyDenied",
            details={"request": req.model_dump(), "reason": decision.reason}
        )
        pgl_hash = pgl_res.get("event_hash", "unverified")
        return RuntimeResponse(type="PolicyDenied", reason=decision.reason, pgl_hash=pgl_hash)

    if decision.decision == "RequireApproval":
        elicitation_id = uuid.uuid4()
        pgl_res = await pgl_client.create_ledger_event(
            agent_id=req.context.actor_id,
            event_type="GovernanceRequired",
            details={"request": req.model_dump(), "elicitation_id": str(elicitation_id)}
        )
        pgl_hash = pgl_res.get("event_hash", "unverified")
        return RuntimeResponse(
            type="GovernanceRequired",
            elicitation_id=elicitation_id,
            message=decision.message,
            pgl_hash=pgl_hash
        )

    # 3. Settlement Plane (Phase 1: Lock)
    # We assume a micro-settlement for each capability call
    ledger_entry = await SettlementService.initialize_channel(
        db=db,
        tenant_id=tenant_id,
        provider=cap.toolset,
        fee_type="capability_invocation",
        amount=100, # 100 micro-USDC as mock fee
        execution_id=req.context.trace_id
    )

    # 4. Execution Plane (Mocked)
    # Phase 2: Execute
    await SettlementService.record_execution(db, ledger_entry.id, f"run_{uuid.uuid4().hex[:8]}")

    try:
        if cap.id == "github.get_repo":
            result = {"name": "interlink-rs", "visibility": "private", "owner": "veklom"}
        elif cap.id == "github.create_issue":
            result = {"issue_no": 42, "status": "created", "internal_token": "SENSITIVE_123"}
        else:
            result = {"status": "completed"}

        # 5. Post-Execution: Output Sanitization
        sanitized_result = enforcer.sanitize_output(result)

        # Phase 3: Bind
        execution_hash = hashlib.sha256(json.dumps(sanitized_result).encode()).hexdigest()
        await SettlementService.bind_execution(db, ledger_entry.id, execution_hash)

        # Seal success evidence
        pgl_res = await pgl_client.create_ledger_event(
            agent_id=req.context.actor_id,
            event_type="Success",
            details={"request_hash": execution_hash, "outcome": "Success"}
        )
        pgl_hash = pgl_res.get("event_hash", "unverified")

        # Phase 4: Settle
        await SettlementService.finalize_settlement(db, ledger_entry.id, 100)

        return RuntimeResponse(
            type="Success",
            result=sanitized_result,
            trace_id=req.context.trace_id,
            pgl_hash=pgl_hash
        )

    except Exception as e:
        logger.error(f"Execution failed: {e}")
        return RuntimeResponse(type="Error", message=str(e))

@router.post("/invoke")
async def invoke_v2(
    req: InvocationRequest,
    user=Depends(get_current_user_or_api_key),
    db: AsyncSession = Depends(get_db)
):
    """VNP v2.0 Capability Invocation Endpoint."""
    # Ensure context actor and tenant match auth
    req.context.actor_id = user.id
    req.context.tenant_id = user.workspace_id
    req.context.transport = TransportType.Http

    response = await execute_capability(db, req, user.workspace_id)
    return response
