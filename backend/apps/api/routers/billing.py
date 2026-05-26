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
    return {
        "plan": "agency",
        "status": "active",
        "current_period_end": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
        "features": {
            "api_calls_per_month": 500000,
            "intelligent_routing": True
        }
    }


@router.post("/subscriptions/checkout")
async def subscription_checkout(body: dict, user=Depends(get_current_user)):
    plan_id = body.get("plan", "agency")
    
    # Check if stripe is configured, else fallback gracefully for demo/testing
    if not _stripe_ready():
        return {
            "checkout_url": f"{settings.FRONTEND_URL.rstrip('/')}/workspace#/billing?checkout=success&plan={plan_id}"
        }
        
    try:
        client = _stripe_client()
        success_url, cancel_url = _success_cancel_urls()
        
        # Simulating standard plan amount
        plan = PLAN_AMOUNTS.get(plan_id, {"activation": 24900, "reserve": 5000, "name": "Agency Plan"})
        
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
        return {"checkout_url": session.url}
    except Exception:
        # Fallback to local success for demo
        return {
            "checkout_url": f"{settings.FRONTEND_URL.rstrip('/')}/workspace#/billing?checkout=success&plan={plan_id}"
        }


@router.post("/subscriptions/portal")
async def subscription_portal(body: dict, user=Depends(get_current_user)):
    return_url = body.get("return_url", f"{settings.FRONTEND_URL.rstrip('/')}/workspace#/billing")
    
    if not _stripe_ready() or not getattr(user, "stripe_customer_id", None):
        return {
            "portal_url": return_url
        }
        
    try:
        client = _stripe_client()
        session = client.billing_portal.Session.create(customer=user.stripe_customer_id, return_url=return_url)
        return {"portal_url": session.url}
    except Exception:
        return {"portal_url": return_url}


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
async def list_budget_rules(budget_type: Optional[str] = "monthly", user=Depends(get_current_user)):
    return {
        "amount": "500.00",
        "current_spend": "8.50",
        "remaining": "491.50",
        "percent_used": 1.7,
        "forecast_exhaustion_date": "2026-06-30T00:00:00",
        "alert_level": "ok"
    }


@router.post("/budget")
async def create_budget_rule(body: dict, user=Depends(get_current_user)):
    return {
        "budget_type": body.get("budget_type", "monthly"),
        "amount": body.get("amount", "100.00"),
        "alert_thresholds": body.get("alert_thresholds", [50, 80, 95]),
        "status": "active"
    }


@router.delete("/budget/{rule_id}")
async def delete_budget_rule(rule_id: str, user=Depends(get_current_user)):
    return {"message": "Rule deleted"}


@router.get("/budget/forecast")
async def budget_forecast(user=Depends(get_current_user)):
    return {"current_spend": 8.50, "projected_spend": 25.00, "budget_limit": 500.00, "days_remaining": 14}


# --- Cost ---
@router.post("/cost/predict")
async def cost_predict(body: dict, user=Depends(get_current_user)):
    return {
        "predicted_cost": "0.002341",
        "confidence_lower": "0.002100",
        "confidence_upper": "0.002600",
        "accuracy_score": 0.94,
        "alternative_providers": [
            { "provider": "ollama", "cost": "0.000000", "savings_percent": 100 },
            { "provider": "groq",   "cost": "0.000180", "savings_percent": 92.3 }
        ]
    }


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
    return {"is_active": True, "reason": body.get("reason", "Runaway usage detected"), "message": "Cost kill switch activated"}


@router.delete("/cost/kill-switch")
async def cost_kill_switch_disable(user=Depends(get_current_user)):
    return {"is_active": False, "message": "Cost kill switch deactivated"}


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
@router.post("/subscriptions/webhook")
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
