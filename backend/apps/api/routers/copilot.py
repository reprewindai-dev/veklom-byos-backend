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


@router.get("/registry/{copilot_id}")
async def get_copilot(copilot_id: str, user=Depends(get_current_user)):
    return {
        "id": copilot_id,
        "status": "active",
        "model": "qwen2.5:3b",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
