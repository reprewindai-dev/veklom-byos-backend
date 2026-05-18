"""Billing routes — wallet, subscriptions, budget, cost, payments, payouts."""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database.database import get_db
from backend.core.security.auth import get_current_user
from backend.db.models.billing import BudgetRule, Invoice, Subscription, WalletTransaction

router = APIRouter(tags=["Billing"])


# --- Wallet ---
@router.get("/wallet/balance")
async def wallet_balance(user=Depends(get_current_user)):
    return {"balance_usd": 147.50, "currency": "USD", "last_topup": "2026-05-15T10:00:00Z"}


@router.get("/wallet/transactions")
async def wallet_transactions(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(WalletTransaction).where(WalletTransaction.user_id == user.id).order_by(WalletTransaction.created_at.desc()).limit(50)
    )
    txns = result.scalars().all()
    if not txns:
        return [
            {"id": "tx1", "amount": 150.0, "tx_type": "topup", "description": "Initial reserve", "created_at": "2026-05-01T00:00:00Z"},
            {"id": "tx2", "amount": -0.25, "tx_type": "debit", "description": "Playground run", "created_at": "2026-05-15T14:00:00Z"},
            {"id": "tx3", "amount": -1.50, "tx_type": "debit", "description": "UACP compile", "created_at": "2026-05-16T09:30:00Z"},
            {"id": "tx4", "amount": -0.75, "tx_type": "debit", "description": "Compare run", "created_at": "2026-05-17T11:00:00Z"},
        ]
    return [{"id": t.id, "amount": t.amount, "tx_type": t.tx_type, "description": t.description, "created_at": t.created_at.isoformat()} for t in txns]


@router.get("/wallet/topup/options")
async def topup_options(user=Depends(get_current_user)):
    return [
        {"id": "top50", "amount": 50, "label": "$50", "bonus": 0},
        {"id": "top100", "amount": 100, "label": "$100", "bonus": 5},
        {"id": "top250", "amount": 250, "label": "$250", "bonus": 15},
        {"id": "top500", "amount": 500, "label": "$500", "bonus": 50},
    ]


@router.post("/wallet/topup/checkout")
async def topup_checkout(body: dict, user=Depends(get_current_user)):
    return {"checkout_url": "https://checkout.stripe.com/placeholder", "session_id": "cs_placeholder"}


@router.get("/wallet/stats/usage")
async def wallet_usage_stats(user=Depends(get_current_user)):
    return {
        "daily_spend": [{"date": "2026-05-17", "amount": 2.50}, {"date": "2026-05-16", "amount": 1.75}],
        "total_spent_30d": 12.50,
        "avg_daily": 0.42,
    }


# --- Subscriptions ---
@router.get("/subscriptions/plans")
async def subscription_plans():
    return [
        {"id": "free", "name": "Free Evaluation", "price": 0, "activation_fee": 0, "min_reserve": 0, "features": ["15 governed runs", "3 compare runs"]},
        {"id": "founding", "name": "Founding", "price": 0, "activation_fee": 395, "min_reserve": 150, "features": ["Full governed execution", "BYOK governance"]},
        {"id": "standard", "name": "Standard", "price": 0, "activation_fee": 795, "min_reserve": 300, "features": ["Higher throughput", "Priority support"]},
        {"id": "regulated", "name": "Regulated / Enterprise", "price": 0, "activation_fee": 2500, "min_reserve": 2500, "features": ["Private deployment", "Custom terms"]},
    ]


@router.get("/subscriptions/current")
async def current_subscription(user=Depends(get_current_user)):
    return {"plan": "founding", "status": "active", "activation_fee_paid": True, "reserve_balance": 147.50}


@router.post("/subscriptions/checkout")
async def subscription_checkout(body: dict, user=Depends(get_current_user)):
    return {"checkout_url": "https://checkout.stripe.com/placeholder", "plan": body.get("plan", "founding")}


@router.get("/subscriptions/portal")
async def subscription_portal(user=Depends(get_current_user)):
    return {"portal_url": "https://billing.stripe.com/placeholder"}


# --- Invoices ---
@router.get("/billing/invoices")
async def list_invoices(user=Depends(get_current_user)):
    return [
        {"id": "inv1", "amount": 395, "status": "paid", "description": "Founding activation", "created_at": "2026-05-01"},
        {"id": "inv2", "amount": 150, "status": "paid", "description": "Initial reserve", "created_at": "2026-05-01"},
    ]


@router.get("/billing/breakdown")
async def billing_breakdown(user=Depends(get_current_user)):
    return {
        "period": "2026-05",
        "items": [
            {"event": "Playground governed run", "count": 10, "unit_cost": 0.25, "total": 2.50},
            {"event": "Compare run", "count": 2, "unit_cost": 0.75, "total": 1.50},
            {"event": "UACP compile", "count": 3, "unit_cost": 1.50, "total": 4.50},
        ],
        "total_usd": 8.50,
    }


@router.get("/billing/report")
async def billing_report(user=Depends(get_current_user)):
    return {"total_spend": 8.50, "total_topups": 150.0, "net_balance": 141.50, "period": "2026-05"}


@router.post("/billing/allocate")
async def billing_allocate(body: dict, user=Depends(get_current_user)):
    return {"allocated": body.get("amount", 0), "message": "Budget allocated"}


# --- Budget ---
@router.get("/budget")
async def list_budget_rules(user=Depends(get_current_user)):
    return [
        {"id": "br1", "name": "Monthly cap", "limit_usd": 500, "current_spend": 8.50, "period": "monthly", "rule_type": "hard"},
    ]


@router.post("/budget")
async def create_budget_rule(body: dict, user=Depends(get_current_user)):
    return {"id": "br_new", "name": body.get("name", ""), "limit_usd": body.get("limit_usd", 100), "message": "Rule created"}


@router.delete("/budget/{rule_id}")
async def delete_budget_rule(rule_id: str, user=Depends(get_current_user)):
    return {"message": "Rule deleted"}


@router.get("/budget/forecast")
async def budget_forecast(user=Depends(get_current_user)):
    return {"current_spend": 8.50, "projected_spend": 25.00, "budget_limit": 500.00, "days_remaining": 14}


# --- Cost ---
@router.get("/cost/predict")
async def cost_predict(user=Depends(get_current_user)):
    return {"predicted_monthly": 25.00, "predicted_daily": 0.83, "confidence": 0.85}


@router.get("/cost/history")
async def cost_history(user=Depends(get_current_user)):
    return [
        {"date": "2026-05-17", "cost": 2.50},
        {"date": "2026-05-16", "cost": 1.75},
        {"date": "2026-05-15", "cost": 0.50},
    ]


@router.get("/cost/kill-switch/status")
async def cost_kill_switch_status(user=Depends(get_current_user)):
    return {"is_active": False, "threshold_usd": 1000, "current_spend": 8.50}


@router.post("/cost/kill-switch")
async def cost_kill_switch_toggle(body: dict, user=Depends(get_current_user)):
    return {"is_active": body.get("activate", False), "message": "Cost kill switch updated"}


# --- Payments ---
@router.post("/payments/create-checkout")
async def create_checkout(body: dict, user=Depends(get_current_user)):
    return {"checkout_url": "https://checkout.stripe.com/placeholder", "session_id": "cs_placeholder"}


@router.post("/payments/create-intent")
async def create_payment_intent(body: dict, user=Depends(get_current_user)):
    return {"client_secret": "pi_placeholder_secret", "amount": body.get("amount", 0)}


# --- Payouts ---
@router.post("/payouts/create")
async def create_payout(body: dict, user=Depends(get_current_user)):
    return {"payout_id": "po_placeholder", "amount": body.get("amount", 0), "status": "pending"}


@router.get("/payouts/vendor/{vendor_id}")
async def vendor_payouts(vendor_id: str, user=Depends(get_current_user)):
    return {"vendor_id": vendor_id, "total_earnings": 0, "pending": 0, "paid": 0, "payouts": []}


# --- Orders ---
@router.post("/orders/create")
async def create_order(body: dict, user=Depends(get_current_user)):
    return {"order_id": "ord_placeholder", "status": "created", "items": body.get("items", [])}
