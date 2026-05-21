"""Token wallet deduction dependencies."""
from fastapi import Depends, HTTPException, status, Request
import logging
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database.database import get_db
from backend.core.security.auth import get_current_user

logger = logging.getLogger(__name__)

# Test Mode corresponds to Phase 5. No actual deduction happens.
TEST_MODE = True

ENDPOINT_CATALOG = {
    "/api/v1/ai/complete": {"token_cost": 25, "plan": "starter"},
    "/api/v1/cost/predict": {"token_cost": 10, "plan": "starter"},
    "/api/v1/exec": {"token_cost": 50, "plan": "pro"},
}

async def token_deduction_guard(
    request: Request,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Intercepts request, calculates cost from catalog, and deducts wallet."""
    endpoint = request.url.path
    
    catalog_entry = ENDPOINT_CATALOG.get(endpoint)
    
    if not catalog_entry:
        return user
        
    token_cost = catalog_entry.get("token_cost", 0)
    
    if token_cost == 0:
        return user
        
    # In a full implementation, we'd query the wallet model:
    # wallet = await db.execute(select(Wallet).where(Wallet.workspace_id == user.default_workspace_id))
    current_balance = 500000  # Mock balance
    
    if current_balance < token_cost:
        if TEST_MODE:
            logger.warning(f"[WALLET_VIOLATION_TEST] Insufficient tokens for {user.id}. Required: {token_cost}. Allowing due to TEST_MODE.")
        else:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Insufficient tokens. Required: {token_cost}, Balance: {current_balance}"
            )
            
    # Mock deduction
    new_balance = current_balance - token_cost
    
    if TEST_MODE:
        logger.info(f"[WALLET_DEDUCTION_TEST] Mock deducted {token_cost} tokens from {user.id} for {endpoint}. New balance: {new_balance}")
    else:
        # wallet.balance = new_balance
        # await db.commit()
        pass
        
    # Append to request state so middleware or response handlers can read it
    request.state.remaining_tokens = new_balance
    return user
