"""Entitlement plan verification dependencies."""
from fastapi import Depends, HTTPException, status
import logging

from backend.core.security.auth import get_current_user

logger = logging.getLogger(__name__)

PLAN_HIERARCHY = {
    "starter": 1,
    "pro": 2,
    "sovereign": 3,
    "enterprise": 4
}

# In Phase 4/5, we do not block traffic. We just log violations.
TEST_MODE = True

def require_entitlement(required_plan: str):
    """Dependency that enforces subscription tier requirements."""
    
    async def _entitlement_checker(user=Depends(get_current_user)):
        # In a fully fleshed out system, we would query the Subscription table here:
        # subscription = await db.execute(select(Subscription).where(Subscription.workspace_id == user.default_workspace_id))
        
        # For now, we assume all users are currently on "starter" unless explicitly upgraded
        current_plan = "starter"
        
        req_level = PLAN_HIERARCHY.get(required_plan, 0)
        cur_level = PLAN_HIERARCHY.get(current_plan, 0)
        
        if cur_level < req_level:
            if TEST_MODE:
                logger.warning(f"[ENTITLEMENT_VIOLATION_TEST] Workspace for user {user.id} lacks '{required_plan}' plan (current: '{current_plan}'). Allowing due to TEST_MODE.")
            else:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"This endpoint requires the {required_plan} plan."
                )
        return user
        
    return _entitlement_checker
