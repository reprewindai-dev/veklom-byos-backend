"""CAPPO Edge - Perimeter Policy Evaluation (Fast, Rule-Based)."""

from datetime import datetime, timezone
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
import time

from backend.core.database.database import get_db
from backend.core.security.auth import get_current_user
from backend.db.models.user import User
from backend.core.security.jti_guard import JtiStore, JtiGuard

router = APIRouter(prefix="/cappo/edge", tags=["CAPPO Edge"])

jti_store = JtiStore()
jti_guard = JtiGuard(jti_store)

@router.post("/policy/validate", response_model=Dict[str, Any])
async def validate_policy(
    policy_request: Dict[str, Any],
    eat_jti: str = Header(None, alias="X-EAT-JTI"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Validate execution against active policies at the perimeter."""
    try:
        required_fields = ["agent_id", "tool_name", "tool_parameters"]
        for field in required_fields:
            if field not in policy_request:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
        
        tool_name = policy_request["tool_name"]
        side_effects_tools = ["system_delete", "external_payment", "deployment"]
        
        # Deny all unmatched tools (Fail Closed, removing implicit ALLOW)
        allowed_tools = ["read_status", "list_metrics", "generate_plan"] + side_effects_tools
        if tool_name not in allowed_tools:
            return {
                "valid": False,
                "violations": [{
                    "rule": "unauthorized_tool",
                    "severity": "high",
                    "message": f"Tool {tool_name} is not in the allowed perimeter policies."
                }],
                "action": "block",
                "policy_version": "v1.2.4"
            }

        # If it has side effects, enforce single-use EAT
        if tool_name in side_effects_tools:
            if not eat_jti:
                return {
                    "valid": False,
                    "violations": [{
                        "rule": "missing_eat",
                        "severity": "critical",
                        "message": f"Tool {tool_name} requires a single-use EAT JTI."
                    }],
                    "action": "block",
                    "policy_version": "v1.2.4"
                }
            
            try:
                # Consume JTI. iat=now, exp=now+300
                now = int(time.time())
                await jti_guard.check_and_commit(
                    iss="cappo-edge",
                    jti=eat_jti,
                    aud="execution",
                    iat=now,
                    exp=now + 300
                )
            except PermissionError as e:
                return {
                    "valid": False,
                    "violations": [{
                        "rule": "replay_detected",
                        "severity": "critical",
                        "message": str(e)
                    }],
                    "action": "block",
                    "policy_version": "v1.2.4"
                }
            except Exception as e:
                return {
                    "valid": False,
                    "violations": [{
                        "rule": "jti_validation_failed",
                        "severity": "high",
                        "message": str(e)
                    }],
                    "action": "block",
                    "policy_version": "v1.2.4"
                }
            
            # Log the dangerous operation approval
            from backend.db.models.security import SecurityEvent
            event = SecurityEvent(
                workspace_id=current_user.workspace_id,
                event_type="policy_audit",
                threat_type="dangerous_operation_approved",
                severity="low",
                description=f"Side-effect tool {tool_name} approved via single-use EAT.",
                details={"jti": eat_jti}
            )
            db.add(event)
            await db.commit()
            
        return {
            "valid": True,
            "violations": [],
            "warnings": [],
            "action": "allow",
            "policy_version": "v1.2.4"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Policy validation failed: {str(e)}")
