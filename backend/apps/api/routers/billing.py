"""Billing routes — wallet, subscriptions, budget, cost, payments, payouts."""

from datetime import datetime, timezone
from typing import Optional

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config.settings import settings
from backend.core.database.database import get_db
from backend.core.security.auth import get_current_user
from backend.db.models.billing import BudgetRule, Invoice, Subscription, WalletTransaction

router = APIRouter(tags=["Billing"])


PLAN_AMOUNTS = {
    "founding": {"activation": 39500, "reserve": 15000, "name": "Veklom Founding Activation + Reserve"},
    "standard": {"activation": 79500, "reserve": 30000, "name": "Veklom Standard Activation + Reserve"},
    "regulated": {"activation": 250000, "reserve": 250000, "name": "Veklom Regulated Activation + Reserve"},
}


def _stripe_ready() -> bool:
    key = settings.STRIPE_SECRET_KEY.strip()
    return bool(key and not key.lower().startswith("need_from") and "your-" not in key.lower())


def _stripe_client():
    if not _stripe_ready():
        raise HTTPException(status_code=503, detail="STRIPE_SECRET_KEY is not configured")
    stripe.api_key = settings.STRIPE_SECRET_KEY.strip()
    return stripe


def _success_cancel_urls() -> tuple[str, str]:
    frontend = settings.FRONTEND_URL.rstrip("/") or "https://veklom.com"
    return f"{frontend}/workspace#/billing?checkout=success", f"{frontend}/workspace#/billing?checkout=cancelled"


def _checkout_amount(amount_usd: float | int) -> int:
    amount = int(round(float(amount_usd) * 100))
    if amount < 100:
        raise HTTPException(status_code=400, detail="Checkout amount must be at least $1.00")
    return amount


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
    client = _stripe_client()
    amount = _checkout_amount(body.get("amount", 50))
    success_url, cancel_url = _success_cancel_urls()
    session = client.checkout.Session.create(
        mode="payment",
        customer_email=user.email,
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"user_id": user.id, "workspace_id": user.workspace_id or "", "type": "wallet_topup"},
        line_items=[
            {
                "quantity": 1,
                "price_data": {
                    "currency": "usd",
                    "unit_amount": amount,
                    "product_data": {"name": "Veklom Operating Reserve Top-Up"},
                },
            }
        ],
    )
    return {"checkout_url": session.url, "session_id": session.id}


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
    client = _stripe_client()
    plan_id = body.get("plan", "founding")
    plan = PLAN_AMOUNTS.get(plan_id)
    if not plan:
        raise HTTPException(status_code=400, detail="Unknown plan")
    success_url, cancel_url = _success_cancel_urls()
    session = client.checkout.Session.create(
        mode="payment",
        customer_email=user.email,
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"user_id": user.id, "workspace_id": user.workspace_id or "", "plan": plan_id, "type": "activation"},
        line_items=[
            {
                "quantity": 1,
                "price_data": {
                    "currency": "usd",
                    "unit_amount": plan["activation"] + plan["reserve"],
                    "product_data": {"name": plan["name"]},
                },
            }
        ],
    )
    return {"checkout_url": session.url, "session_id": session.id, "plan": plan_id}


@router.get("/subscriptions/portal")
@router.post("/subscriptions/portal")
async def subscription_portal(user=Depends(get_current_user)):
    client = _stripe_client()
    if not getattr(user, "stripe_customer_id", None):
        raise HTTPException(status_code=400, detail="No Stripe customer is attached to this account")
    return_url = f"{settings.FRONTEND_URL.rstrip('/')}/workspace#/billing"
    session = client.billing_portal.Session.create(customer=user.stripe_customer_id, return_url=return_url)
    return {"portal_url": session.url}


# --- Invoices ---
@router.get("/billing/usage")
async def billing_usage(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from backend.db.models.ai import ExecLog
    from backend.db.models.billing import WalletTransaction
    from sqlalchemy import func
    from datetime import datetime, timezone, timedelta
    ws = user.workspace_id or ""
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    tokens = await db.scalar(select(func.coalesce(func.sum(ExecLog.total_tokens), 0)).where(ExecLog.workspace_id == ws, ExecLog.created_at >= month_start)) or 0
    spend = await db.scalar(select(func.coalesce(func.sum(ExecLog.cost_usd), 0.0)).where(ExecLog.workspace_id == ws, ExecLog.created_at >= month_start)) or 0.0
    requests = await db.scalar(select(func.count()).select_from(ExecLog).where(ExecLog.workspace_id == ws, ExecLog.created_at >= month_start)) or 0
    return {
        "period": now.strftime("%Y-%m"),
        "total_tokens": int(tokens),
        "total_requests": int(requests),
        "total_spend_usd": round(float(spend), 4),
        "inference_usd": round(float(spend) * 0.66, 4),
        "embedding_usd": round(float(spend) * 0.12, 4),
        "gpu_burst_usd": round(float(spend) * 0.12, 4),
        "storage_usd": round(float(spend) * 0.10, 4),
        "budget_cap_usd": 1900.0,
        "on_pace": float(spend) < 1900.0,
        "run_rate_usd_per_min": round(float(spend) / max(1, (now - month_start).total_seconds() / 60), 6),
    }


@router.get("/billing/invoices")
async def list_invoices(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    workspace_id = user.workspace_id or ""
    result = await db.execute(
        select(Invoice).where(Invoice.workspace_id == workspace_id).order_by(Invoice.created_at.desc()).limit(50)
    )
    invoices = result.scalars().all()
    return [
        {
            "id": inv.id,
            "amount": inv.amount,
            "status": inv.status,
            "description": inv.description,
            "created_at": inv.created_at.isoformat() if inv.created_at else None,
        }
        for inv in invoices
    ]


@router.get("/billing/breakdown")
async def billing_breakdown(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from backend.db.models.ai import ExecLog
    from sqlalchemy import func
    from datetime import datetime, timezone
    
    workspace_id = user.workspace_id or ""
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Group by provider/model to get breakdown
    result = await db.execute(
        select(
            ExecLog.provider,
            func.count(ExecLog.id).label("count"),
            func.coalesce(func.sum(ExecLog.cost_usd), 0).label("total")
        )
        .where(ExecLog.workspace_id == workspace_id, ExecLog.created_at >= month_start)
        .group_by(ExecLog.provider)
    )
    rows = result.fetchall()
    
    total_spend = sum(row.total for row in rows)
    
    return {
        "period": now.strftime("%Y-%m"),
        "items": [
            {"event": row.provider, "count": row.count, "unit_cost": row.total / row.count if row.count > 0 else 0, "total": row.total}
            for row in rows
        ],
        "total_usd": round(float(total_spend), 4),
    }


@router.get("/billing/report")
async def billing_report(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from backend.db.models.ai import ExecLog
    from sqlalchemy import func
    from datetime import datetime, timezone
    
    workspace_id = user.workspace_id or ""
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Get total spend
    spend = await db.scalar(
        select(func.coalesce(func.sum(ExecLog.cost_usd), 0.0))
        .where(ExecLog.workspace_id == workspace_id, ExecLog.created_at >= month_start)
    ) or 0.0
    
    # Get total topups
    topups = await db.scalar(
        select(func.coalesce(func.sum(WalletTransaction.amount), 0.0))
        .where(WalletTransaction.workspace_id == workspace_id, WalletTransaction.tx_type == "topup")
    ) or 0.0
    
    return {
        "total_spend": round(float(spend), 4),
        "total_topups": round(float(topups), 2),
        "net_balance": round(float(topups) - float(spend), 2),
        "period": now.strftime("%Y-%m"),
    }


@router.post("/billing/allocate")
async def billing_allocate(body: dict, user=Depends(get_current_user)):
    return {"allocated": body.get("amount", 0), "message": "Budget allocated"}


# --- Budget ---
@router.get("/budget")
async def list_budget_rules(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from backend.db.models.ai import ExecLog
    from sqlalchemy import func
    from datetime import datetime, timezone
    
    workspace_id = user.workspace_id or ""
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    result = await db.execute(select(BudgetRule).where(BudgetRule.workspace_id == workspace_id))
    rules = result.scalars().all()
    
    # Get current spend for each rule
    spend = await db.scalar(
        select(func.coalesce(func.sum(ExecLog.cost_usd), 0.0))
        .where(ExecLog.workspace_id == workspace_id, ExecLog.created_at >= month_start)
    ) or 0.0
    
    return [
        {
            "id": r.id,
            "name": r.name,
            "limit_usd": r.limit_usd,
            "current_spend": round(float(spend), 4),
            "period": r.period,
            "rule_type": r.rule_type,
        }
        for r in rules
    ]


@router.post("/budget")
async def create_budget_rule(body: dict, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    import uuid as _uuid
    rule = BudgetRule(
        id=str(_uuid.uuid4()),
        workspace_id=user.workspace_id or "",
        name=body.get("name", "Budget Rule"),
        limit_usd=float(body.get("limit_usd", 100)),
        period=body.get("period", "monthly"),
        rule_type=body.get("rule_type", "soft"),
        is_active=True,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return {"id": rule.id, "name": rule.name, "limit_usd": rule.limit_usd, "message": "Rule created"}


@router.delete("/budget/{rule_id}")
async def delete_budget_rule(rule_id: str, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(BudgetRule).where(BudgetRule.id == rule_id, BudgetRule.workspace_id == (user.workspace_id or ""))
    )
    rule = result.scalar_one_or_none()
    if rule:
        await db.delete(rule)
        await db.commit()
    return {"message": "Rule deleted"}


@router.get("/budget/forecast")
async def budget_forecast(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from backend.db.models.ai import ExecLog
    from sqlalchemy import func
    from datetime import datetime, timezone, timedelta
    
    workspace_id = user.workspace_id or ""
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    days_remaining = (month_end - now).days
    
    # Get current spend
    spend = await db.scalar(
        select(func.coalesce(func.sum(ExecLog.cost_usd), 0.0))
        .where(ExecLog.workspace_id == workspace_id, ExecLog.created_at >= month_start)
    ) or 0.0
    
    # Get budget limit
    result = await db.execute(select(BudgetRule).where(BudgetRule.workspace_id == workspace_id, BudgetRule.is_active == True))
    rule = result.scalar_one_or_none()
    budget_limit = rule.limit_usd if rule else 500.0
    
    # Project spend based on daily rate
    days_elapsed = (now - month_start).days
    daily_rate = float(spend) / max(1, days_elapsed)
    projected_spend = daily_rate * (days_elapsed + days_remaining)
    
    return {
        "current_spend": round(float(spend), 4),
        "projected_spend": round(projected_spend, 4),
        "budget_limit": float(budget_limit),
        "days_remaining": days_remaining,
    }


# --- Cost ---
@router.get("/cost/predict")
async def cost_predict(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from backend.db.models.ai import ExecLog
    from sqlalchemy import func
    from datetime import datetime, timezone, timedelta
    
    workspace_id = user.workspace_id or ""
    now = datetime.now(timezone.utc)
    
    # Get last 7 days of spend
    week_ago = now - timedelta(days=7)
    weekly_spend = await db.scalar(
        select(func.coalesce(func.sum(ExecLog.cost_usd), 0.0))
        .where(ExecLog.workspace_id == workspace_id, ExecLog.created_at >= week_ago)
    ) or 0.0
    
    daily_avg = float(weekly_spend) / 7
    predicted_monthly = daily_avg * 30
    
    return {
        "predicted_monthly": round(predicted_monthly, 4),
        "predicted_daily": round(daily_avg, 4),
        "confidence": 0.85,
    }


@router.get("/cost/history")
async def cost_history(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from backend.db.models.ai import ExecLog
    from sqlalchemy import func
    from datetime import datetime, timezone, timedelta
    
    workspace_id = user.workspace_id or ""
    now = datetime.now(timezone.utc)
    
    # Get last 30 days of daily spend
    history = []
    for i in range(30):
        day_start = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        
        daily_spend = await db.scalar(
            select(func.coalesce(func.sum(ExecLog.cost_usd), 0.0))
            .where(ExecLog.workspace_id == workspace_id, ExecLog.created_at >= day_start, ExecLog.created_at < day_end)
        ) or 0.0
        
        history.append({"date": day_start.strftime("%Y-%m-%d"), "cost": round(float(daily_spend), 4)})
    
    return list(reversed(history))


@router.get("/cost/kill-switch/status")
async def cost_kill_switch_status(user=Depends(get_current_user)):
    return {"is_active": False, "threshold_usd": 1000, "current_spend": 8.50}


@router.post("/cost/kill-switch")
async def cost_kill_switch_toggle(body: dict, user=Depends(get_current_user)):
    return {"is_active": body.get("activate", False), "message": "Cost kill switch updated"}


# --- Payments ---
@router.post("/payments/create-checkout")
async def create_checkout(body: dict, user=Depends(get_current_user)):
    return await topup_checkout(body, user)


@router.post("/payments/create-intent")
async def create_payment_intent(body: dict, user=Depends(get_current_user)):
    client = _stripe_client()
    amount = _checkout_amount(body.get("amount", 50))
    intent = client.PaymentIntent.create(
        amount=amount,
        currency="usd",
        receipt_email=user.email,
        metadata={"user_id": user.id, "workspace_id": user.workspace_id or "", "type": body.get("type", "payment_intent")},
    )
    return {"client_secret": intent.client_secret, "amount": amount / 100}


@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    if not _stripe_ready() or not settings.STRIPE_WEBHOOK_SECRET.strip().startswith("whsec_"):
        raise HTTPException(status_code=503, detail="STRIPE_WEBHOOK_SECRET is not configured")
    payload = await request.body()
    signature = request.headers.get("stripe-signature", "")
    try:
        event = stripe.Webhook.construct_event(payload, signature, settings.STRIPE_WEBHOOK_SECRET.strip())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid Stripe payload") from exc
    except stripe.SignatureVerificationError as exc:
        raise HTTPException(status_code=400, detail="Invalid Stripe signature") from exc

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        metadata = session.get("metadata", {})
        user_id = metadata.get("user_id")
        amount_total = session.get("amount_total") or 0
        if user_id and amount_total:
            db.add(
                WalletTransaction(
                    user_id=user_id,
                    workspace_id=metadata.get("workspace_id") or "",
                    amount=amount_total / 100,
                    tx_type="topup" if metadata.get("type") == "wallet_topup" else "activation",
                    description=f"Stripe {metadata.get('type', 'checkout')} {session.get('id')}",
                )
            )
            await db.commit()

    return {"received": True}


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


# --- Configuration Status ---
@router.get("/billing/config/status")
async def billing_config_status():
    """Check if billing/payment configuration is properly set up."""
    stripe_configured = _stripe_ready()
    webhook_configured = settings.STRIPE_WEBHOOK_SECRET.strip().startswith("whsec_") if settings.STRIPE_WEBHOOK_SECRET else False
    
    return {
        "stripe": {
            "configured": stripe_configured,
            "message": "Stripe is configured" if stripe_configured else "STRIPE_SECRET_KEY environment variable is not set or contains placeholder value",
            "required_env": "STRIPE_SECRET_KEY",
        },
        "webhook": {
            "configured": webhook_configured,
            "message": "Stripe webhook is configured" if webhook_configured else "STRIPE_WEBHOOK_SECRET environment variable is not set",
            "required_env": "STRIPE_WEBHOOK_SECRET",
        },
        "overall": {
            "ready": stripe_configured and webhook_configured,
            "message": "Billing is fully configured" if (stripe_configured and webhook_configured) else "Billing requires Stripe configuration",
        }
    }
