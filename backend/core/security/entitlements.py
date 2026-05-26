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

# Plan derivation rules (role-based fallback only — real plan comes from Subscription DB):
#   SUPER_ADMIN         → sovereign (platform superuser, not a tenant role)
#   OWNER / ADMIN       → free (workspace role; real plan set by active Stripe subscription)
#   USER / ANALYST      → starter (paid customer role, Ollama + BYOK)
#   VIEWER / other      → free (eval session, limited runs)
#
# NOTE: The /api/v1/auth/me endpoint performs a real Subscription DB lookup and
# returns the correct plan. This role-based fallback is used only as a last resort
# when no DB session is available (e.g. middleware context).

def _plan_from_role(role: str) -> str:
    """Return a conservative role-based plan fallback.

    OWNER maps to free because workspace ownership alone does not imply a paid
    subscription. The real plan must be read from the Subscription table.
    SUPER_ADMIN keeps sovereign because it is the platform-level role, not a
    self-registered tenant role.
    """
    role = (role or "").upper()
    if role == "SUPER_ADMIN":
        return "sovereign"
    if role in ("USER", "ANALYST"):
        return "starter"
    # OWNER, ADMIN, VIEWER, and unknown roles → free (conservative default)
    return "free"


def require_entitlement(required_plan: str):
    """Dependency that enforces subscription tier requirements.

    Derives the effective plan from the user's role as a conservative fallback.
    Free-tier (eval) users are allowed on starter-level endpoints (playground,
    models) but warned. Pro/sovereign features require an active subscription.
    """

    async def _entitlement_checker(user=Depends(get_current_user)):
        current_plan = _plan_from_role(getattr(user, "role", ""))

        req_level = PLAN_HIERARCHY.get(required_plan, 0)
        cur_level = PLAN_HIERARCHY.get(current_plan, 0)

        if cur_level < req_level:
            # Free users can still access starter endpoints (playground etc.)
            # but log the violation. Block only for pro/sovereign features.
            if cur_level == 0 and req_level <= 1:
                logger.info(
                    f"[ENTITLEMENT_FREE_ACCESS] User {user.id} (free) accessing "
                    f"starter endpoint. Allowing."
                )
            else:
                logger.warning(
                    f"[ENTITLEMENT_BLOCKED] User {user.id} plan={current_plan} "
                    f"tried {required_plan}."
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=(
                        f"This feature requires the {required_plan} plan. "
                        f"Current: {current_plan}. "
                        "Visit /workspace/#/billing to upgrade."
                    ),
                )
        return user

    return _entitlement_checker
