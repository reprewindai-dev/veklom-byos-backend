"""Entitlement plan verification dependencies."""
from fastapi import Depends, HTTPException, status
import logging

from backend.core.security.auth import get_current_user

logger = logging.getLogger(__name__)

PLAN_HIERARCHY = {
    "free": 0,
    "starter": 1,
    "pro": 2,
    "sovereign": 3,
    "enterprise": 4
}

# Plan derivation rules:
#   OWNER / SUPER_ADMIN → sovereign (full access, all provider keys)
#   ADMIN               → pro (full workspace access)
#   USER / ANALYST      → starter (paid customer, Ollama + BYOK)
#   VIEWER / other      → free (eval session, limited runs)

def _plan_from_role(role: str) -> str:
    role = (role or "").upper()
    if role in ("OWNER", "SUPER_ADMIN"):
        return "sovereign"
    if role in ("ADMIN",):
        return "pro"
    if role in ("USER", "ANALYST"):
        return "starter"
    return "free"


def require_entitlement(required_plan: str):
    """Dependency that enforces subscription tier requirements.

    Derives the effective plan from the user's role. Free-tier (eval) users
    are allowed on starter-level endpoints (playground, models) but warned.
    """

    async def _entitlement_checker(user=Depends(get_current_user)):
        current_plan = _plan_from_role(getattr(user, "role", ""))

        req_level = PLAN_HIERARCHY.get(required_plan, 0)
        cur_level = PLAN_HIERARCHY.get(current_plan, 0)

        if cur_level < req_level:
            # Free users can still access starter endpoints (playground etc.)
            # but log the violation. Block only for pro/sovereign features.
            if cur_level == 0 and req_level <= 1:
                logger.info(f"[ENTITLEMENT_FREE_ACCESS] User {user.id} (free) accessing starter endpoint. Allowing.")
            else:
                logger.warning(f"[ENTITLEMENT_BLOCKED] User {user.id} plan={current_plan} tried {required_plan}.")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"This feature requires the {required_plan} plan. Current: {current_plan}."
                )
        return user

    return _entitlement_checker
