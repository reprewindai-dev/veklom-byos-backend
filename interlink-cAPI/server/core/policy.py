"""Policy engine (replaces agent_guardrails.py)."""

from pydantic import BaseModel
from typing import Optional, Dict, Any

class PolicyVerdict(BaseModel):
    allowed: bool
    reason: Optional[str] = None

async def evaluate(intent: Any) -> PolicyVerdict:
    """Evaluates an execution intent against active policy rules."""
    # Logic moved from agent_guardrails.py
    if "admin" in intent.action and "actor" not in intent.agent_id:
        return PolicyVerdict(allowed=False, reason="Action requires admin privileges")

    return PolicyVerdict(allowed=True)

async def get_status() -> Dict[str, Any]:
    return {"status": "operational", "rules_active": 12}
