"""Copilot / AI assistant registry endpoints."""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from backend.core.security.auth import get_current_user

router = APIRouter(prefix="/copilot", tags=["Copilot"])


@router.get("/registry")
async def copilot_registry(user=Depends(get_current_user)):
    return {
        "copilots": [
            {
                "id": "veklom-code-reviewer",
                "name": "Code Review Copilot",
                "description": "Reviews code for security, compliance, and policy violations",
                "model": "qwen2.5:3b",
                "status": "active",
                "capabilities": ["code_review", "security_scan", "policy_check"],
            },
            {
                "id": "veklom-policy-advisor",
                "name": "Policy Advisor",
                "description": "Explains policy decisions and suggests compliant alternatives",
                "model": "qwen2.5:3b",
                "status": "active",
                "capabilities": ["policy_explain", "compliance_advice"],
            },
        ],
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/recent-decisions")
async def copilot_recent_decisions(user=Depends(get_current_user)):
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    return {
        "decisions": [
            {
                "id": f"dec_{i:04d}",
                "action": action,
                "result": result,
                "policy": policy,
                "copilot_id": "veklom-policy-advisor",
                "ts": (now - timedelta(minutes=i * 7)).isoformat(),
            }
            for i, (action, result, policy) in enumerate([
                ("code_review", "approved", "passed"),
                ("inference_request", "executed", "passed"),
                ("pipeline_trigger", "blocked", "policy_violation"),
                ("evidence_export", "approved", "passed"),
                ("compliance_check", "approved", "passed"),
            ])
        ],
        "total": 5,
        "updated_at": now.isoformat(),
    }


@router.get("/registry/{copilot_id}")
async def get_copilot(copilot_id: str, user=Depends(get_current_user)):
    return {
        "id": copilot_id,
        "status": "active",
        "model": "qwen2.5:3b",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
