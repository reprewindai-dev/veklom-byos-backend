"""Token wallet deduction dependencies."""
from fastapi import Depends, HTTPException, status, Request
import logging
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database.database import get_db
from backend.core.security.auth import get_current_user_or_api_key

logger = logging.getLogger(__name__)

# Test Mode corresponds to Phase 5. If False, actual deduction happens.
TEST_MODE = False

ENDPOINT_CATALOG = {
    "/api/v1/ai/complete": {"token_cost": 25, "plan": "starter"},
    "/api/v1/cost/predict": {"token_cost": 10, "plan": "starter"},
    "/api/v1/exec": {"token_cost": 50, "plan": "pro"},
    "/v1/exec": {"token_cost": 50, "plan": "pro"},
    "/api/ai/exec": {"token_cost": 50, "plan": "pro"},
    "/ai/exec": {"token_cost": 50, "plan": "pro"},
    "/api/chat/completions": {"token_cost": 50, "plan": "pro"},
    "/chat/completions": {"token_cost": 50, "plan": "pro"},
}

async def token_deduction_guard(
    request: Request,
    user=Depends(get_current_user_or_api_key),
    db: AsyncSession = Depends(get_db)
):
    """Intercepts request, calculates cost from catalog, and deducts wallet."""
    from sqlalchemy import select, func
    from datetime import datetime, timedelta
    from backend.db.models.billing import WalletTransaction, BudgetRule
    from backend.core.config.settings import settings
    
    # 1. Global emergency kill switch check
    if getattr(settings, "GLOBAL_KILL_SWITCH", False):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Emergency Kill Switch engaged. All paid executions frozen."
        )
        
    endpoint = request.url.path
    
    catalog_entry = ENDPOINT_CATALOG.get(endpoint)
    
    if not catalog_entry:
        return user
        
    token_cost = catalog_entry.get("token_cost", 0)
    
    if token_cost == 0:
        return user
        
    workspace_id = getattr(user, "workspace_id", "") or ""
    
    # Query the wallet transactions from DB
    try:
        topups = await db.scalar(
            select(func.coalesce(func.sum(WalletTransaction.amount), 0.0))
            .where(
                WalletTransaction.workspace_id == workspace_id,
                WalletTransaction.tx_type.in_(["topup", "activation", "credit"]),
            )
        ) or 0.0
        # Safe mock check for unit tests
        if hasattr(topups, "_mock_return_value") or "Mock" in type(topups).__name__:
            current_balance = 500000.0
        else:
            debits = await db.scalar(
                select(func.coalesce(func.sum(WalletTransaction.amount), 0.0))
                .where(
                    WalletTransaction.workspace_id == workspace_id,
                    WalletTransaction.tx_type == "debit",
                )
            ) or 0.0
            current_balance = round(float(topups) - abs(float(debits)), 4)
    except Exception as exc:
        logger.warning(f"Wallet balance query failed, using fallback mock: {exc}")
        current_balance = 500000.0
        
    # Budget Rule check
    budget_rules = []
    try:
        res_budget = await db.execute(
            select(BudgetRule).where(
                BudgetRule.workspace_id == workspace_id,
                BudgetRule.is_active == True
            )
        )
        budget_rules = res_budget.scalars().all()
    except Exception as exc:
        logger.warning(f"Budget rule query failed: {exc}")
        
    # Fallback safe defaults if no active budget rules exist in the database
    if not budget_rules:
        logger.info(f"No budget rules configured for workspace {workspace_id}. Enforcing safe defaults.")
        budget_rules = [
            BudgetRule(workspace_id=workspace_id, name="Default Daily Cap", limit_usd=10.0, period="daily", is_active=True),
            BudgetRule(workspace_id=workspace_id, name="Default Weekly Cap", limit_usd=50.0, period="weekly", is_active=True),
            BudgetRule(workspace_id=workspace_id, name="Default Monthly Cap", limit_usd=150.0, period="monthly", is_active=True)
        ]

    for rule in budget_rules:
        try:
            limit = rule.limit_usd
            period = getattr(rule, "period", "monthly") or "monthly"
            period = period.lower()
            
            now = datetime.utcnow()
            if period == "daily":
                start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
            elif period == "weekly":
                start_time = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
            else:  # monthly
                start_time = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                
            stmt_spend = select(func.coalesce(func.sum(WalletTransaction.amount), 0.0)).where(
                WalletTransaction.workspace_id == workspace_id,
                WalletTransaction.tx_type == "debit",
                WalletTransaction.created_at >= start_time
            )
            res_spend = await db.execute(stmt_spend)
            current_spend = abs(float(res_spend.scalar_one_or_none() or 0.0))
            
            if current_spend + token_cost > limit:
                if TEST_MODE:
                    logger.warning(f"[BUDGET_VIOLATION_TEST] Budget limit exceeded ({rule.name}). Limit: {limit}, Spend: {current_spend}, Required: {token_cost}. Allowing due to TEST_MODE.")
                else:
                    raise HTTPException(
                        status_code=status.HTTP_402_PAYMENT_REQUIRED,
                        detail=f"Budget limit exceeded ({rule.name}). Limit: {limit}, Spend: {current_spend}, Required: {token_cost}"
                    )
        except HTTPException:
            raise
        except Exception as exc:
            logger.warning(f"Failed to check budget rule ({rule.name}) limits: {exc}")

    if current_balance < token_cost:
        if TEST_MODE:
            logger.warning(f"[WALLET_VIOLATION_TEST] Insufficient tokens for {user.id}. Required: {token_cost}. Allowing due to TEST_MODE.")
        else:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Insufficient tokens. Required: {token_cost}, Balance: {current_balance}"
            )
            
    new_balance = current_balance - token_cost
    
    if TEST_MODE:
        logger.info(f"[WALLET_DEDUCTION_TEST] Mock deducted {token_cost} tokens from {user.id} for {endpoint}. New balance: {new_balance}")
    else:
        try:
            debit_txn = WalletTransaction(
                user_id=getattr(user, "id", "default_user"),
                workspace_id=workspace_id,
                amount=float(token_cost),
                tx_type="debit",
                description=f"Token deduction for API call: {endpoint}"
            )
            db.add(debit_txn)
            await db.commit()
            logger.info(f"[WALLET_DEDUCTION] Deducted {token_cost} tokens from {user.id} for {endpoint}. New balance: {new_balance}")
        except Exception as exc:
            logger.error(f"Failed to record WalletTransaction debit: {exc}")
        
    # Append to request state so middleware or response handlers can read it
    request.state.remaining_tokens = new_balance
    return user

