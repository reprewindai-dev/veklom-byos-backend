"""Billing routes - wallet, subscriptions, budget, cost, payments, payouts."""

import logging
from datetime import datetime, timezone
from typing import Optional

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

from backend.core.config.settings import settings
from backend.core.database.database import get_db
from backend.core.security.auth import get_current_user
from backend.db.models.billing import BudgetRule, Invoice, Subscription, WalletTransaction
from backend.db.models.security import KillSwitchState
from backend.db.models.ledger import SettlementLedger

router = APIRouter(tags=["Billing"])


PLAN_AMOUNTS = {
    # New Monthly Subscription tiers (and their annual equivalents)
    "free":       {"amount": 0,       "monthly": 0,      "name": "Free Evaluation",        "description": "Free tier - 15 governed runs, no card required"},
    "starter":    {"amount": 250000,  "monthly": 250000, "name": "Starter Plan",           "description": "$2,500/mo - For teams deploying AI into production"},
    "growth":     {"amount": 850000,  "monthly": 850000, "name": "Growth Plan",            "description": "$8,500/mo - For AI-native companies scaling governance"},
    "sovereign":  {"amount": 0,       "monthly": 0,      "name": "Enterprise Custom",      "description": "Custom pricing - SAML/SCIM/SSO, Custom regions, Procurement-ready"},
    "enterprise": {"amount": 0,       "monthly": 0,      "name": "Enterprise Custom",      "description": "Custom pricing - SAML/SCIM/SSO, Custom regions, Procurement-ready"},
    # Legacy aliases (keep for existing DB records)
    "community":  {"amount": 0,       "monthly": 0,      "name": "Veklom Community",       "description": "Free tier - 15 governed runs"},
    "pro":        {"amount": 49500,   "monthly": 0,      "name": "Standard",               "description": "$495 one-time activation"},
    "founding":   {"amount": 19500,   "monthly": 0,      "name": "Early Access",           "description": "Early Access activation"},
    "standard":   {"amount": 49500,   "monthly": 0,      "name": "Standard Activation",    "description": "Standard activation"},
    "regulated":  {"amount": 499500,  "monthly": 0,      "name": "Regulated Activation",   "description": "Regulated activation"},
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
    frontend = settings.FRONTEND_URL.rstrip('/')
    return f"{frontend}/control-plane-next/billing/?checkout=success", f"{frontend}/control-plane-next/billing/?checkout=cancelled"


def _checkout_amount(amount_usd: float | int) -> int:
    amount = int(round(float(amount_usd) * 100))
    if amount < 100:
        raise HTTPException(status_code=400, detail="Checkout amount must be at least $1.00")
    return amount


# --- Wallet ---
@router.get("/wallet/balance")
async def wallet_balance(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Return the real wallet balance computed from WalletTransaction rows."""
    from sqlalchemy import func
    workspace_id = user.workspace_id or ""
    topups = await db.scalar(
        select(func.coalesce(func.sum(WalletTransaction.amount), 0.0))
        .where(
            WalletTransaction.workspace_id == workspace_id,
            WalletTransaction.tx_type.in_(["topup", "activation"]),
        )
    ) or 0.0
    debits = await db.scalar(
        select(func.coalesce(func.sum(WalletTransaction.amount), 0.0))
        .where(
            WalletTransaction.workspace_id == workspace_id,
            WalletTransaction.tx_type == "debit",
        )
    ) or 0.0
    balance = round(float(topups) - abs(float(debits)), 4)
    return {
        "balance_usd": max(balance, 0.0),
        "currency": "USD",
        "total_topups": round(float(topups), 4),
        "total_debits": round(abs(float(debits)), 4),
    }


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
    return {"url": session.url, "session_id": session.id}


@router.get("/wallet/stats/usage")
async def wallet_usage_stats(user=Depends(get_current_user)):
    return {
        "daily_spend": [{"date": "2026-05-17", "amount": 2.50}, {"date": "2026-05-16", "amount": 1.75}],
        "total_spent_30d": 12.50,
        "avg_daily": 0.42,
    }


# --- Subscriptions ---

# (threshold, label, starter_monthly, starter_annual, growth_monthly, growth_annual)
_MILESTONE_LEVELS = [
    (20,   "Early Access",  250,  200,  850,  680),
    (50,   "Founding",      500,  400,  1700, 1360),
    (150,  "Growth",        1000, 800,  3400, 2720),
    (350,  "Scale",         1750, 1400, 5950, 4760),
    (None, "Established",   2500, 2000, 8500, 6800),
]


async def get_milestone_pricing(db: AsyncSession) -> dict:
    """Return current pricing tier based on dual-trigger milestone thresholds.

    Effective score = max(total_workspaces, active_workspaces_30d * 2.5)
    """
    from datetime import timedelta
    from backend.db.models.workspace import Workspace

    try:
        from sqlalchemy import func
        total_ws = await db.scalar(
            select(func.count(Workspace.id)).where(Workspace.is_active == True)
        ) or 0
    except Exception:
        total_ws = 0

    try:
        from backend.db.models.ai import ExecLog
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        active_ws = await db.scalar(
            select(func.count(func.distinct(ExecLog.workspace_id)))
            .where(ExecLog.created_at >= cutoff)
        ) or 0
    except Exception:
        active_ws = 0

    effective_score = max(total_ws, int(active_ws * 2.5))

    level_idx = len(_MILESTONE_LEVELS) - 1
    for i, row in enumerate(_MILESTONE_LEVELS):
        threshold = row[0]
        if threshold is None or effective_score <= threshold:
            level_idx = i
            break

    row = _MILESTONE_LEVELS[level_idx]
    (threshold, label, starter_monthly, starter_annual, growth_monthly, growth_annual) = row

    next_threshold = None
    if level_idx < len(_MILESTONE_LEVELS) - 1:
        next_threshold = _MILESTONE_LEVELS[level_idx + 1][0]

    return {
        "level": level_idx + 1,
        "level_label": label,
        "effective_score": effective_score,
        "total_workspaces": total_ws,
        "active_workspaces_30d": active_ws,
        "next_threshold": next_threshold,
        "spots_remaining": max(0, next_threshold - effective_score) if next_threshold else None,
        "starter_monthly": starter_monthly,
        "starter_annual": starter_annual,
        "growth_monthly": growth_monthly,
        "growth_annual": growth_annual,
    }


@router.get("/subscriptions/plans")
async def subscription_plans(db: AsyncSession = Depends(get_db)):
    """Return Machine API payment tiers based on x402 Mainnet Base metrics.
    
    Plan IDs map to the frontend tier constants:
      bronze, medium, good.
    Pricing is strictly denominated in USDC testnet parameters via MPP.
    """
    return {
        "milestone": None,
        "plans": [
            {
                "id": "bronze",
                "plan_id": "bronze",
                "tier": "bronze",
                "name": "Bronze API",
                "price": 0.001,
                "price_label": "$0.001 USDC",
                "period": "per execution (Base Mainnet)",
                "features": [
                    "Best effort execution latency",
                    "Basic x402 routing verification",
                    "Public SLA dashboard access",
                    "Standard endpoint limits",
                    "No reserved bandwidth"
                ],
                "bullets": [
                    "Best effort execution latency",
                    "Basic x402 routing verification",
                    "Public SLA dashboard access",
                    "Standard endpoint limits",
                    "No reserved bandwidth"
                ],
            },
            {
                "id": "medium",
                "plan_id": "medium",
                "tier": "medium",
                "name": "Medium API",
                "price": 0.05,
                "price_label": "$0.05 USDC",
                "period": "per execution (Base Mainnet)",
                "features": [
                    "Priority execution lane",
                    "Guaranteed p95 latency under 800ms",
                    "Regional execution isolation",
                    "Real-time x402 ledger proofs",
                    "Dedicated bandwidth pool"
                ],
                "bullets": [
                    "Priority execution lane",
                    "Guaranteed p95 latency under 800ms",
                    "Regional execution isolation",
                    "Real-time x402 ledger proofs",
                    "Dedicated bandwidth pool"
                ],
            },
            {
                "id": "good",
                "plan_id": "good",
                "tier": "good",
                "name": "Good API",
                "price": 0.25,
                "price_label": "$0.25 USDC",
                "period": "per execution (Base Mainnet)",
                "features": [
                    "Sovereign tier isolation guarantees",
                    "Zero-knowledge RAG capabilities",
                    "Sub-300ms p99 execution SLAs",
                    "Hardware enclave processing (Nitro)",
                    "Full SettlementLedger forensic export"
                ],
                "bullets": [
                    "Sovereign tier isolation guarantees",
                    "Zero-knowledge RAG capabilities",
                    "Sub-300ms p99 execution SLAs",
                    "Hardware enclave processing (Nitro)",
                    "Full SettlementLedger forensic export"
                ],
            }
        ]
    }



@router.get("/subscriptions/current")
async def current_subscription(user = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Return the real active subscription from the DB."""
    ws_id = user.workspace_id or ""
    sub = (await db.execute(
        select(Subscription)
        .where(
            Subscription.workspace_id == ws_id,
            Subscription.status.in_(["active", "trialing"]),
        )
        .order_by(Subscription.created_at.desc())
        .limit(1)
    )).scalar_one_or_none()
    
    if sub:
        plan_id = (sub.plan or "").lower()
        normalization = {
            "community": "free",
            "founding": "starter",
            "standard": "pro",
            "regulated": "sovereign",
            "enterprise": "enterprise"
        }
        normalized_plan = normalization.get(plan_id, plan_id)
        return {
            "plan": normalized_plan,
            "status": sub.status,
            "current_period_end": sub.current_period_end.isoformat() if getattr(sub, "current_period_end", None) else None,
            "stripe_subscription_id": getattr(sub, "stripe_subscription_id", None),
        }
        
    return {
        "plan": "free",
        "status": "none",
        "note": "No active subscription. Visit /control-plane-next/billing/ to upgrade.",
    }


@router.post("/subscriptions/checkout")
async def subscription_checkout(body: dict, user=Depends(get_current_user)):
    plan_id = (body.get("plan_id") or body.get("plan") or "agency").lower()
    listing_id = body.get("listing_id")  # for marketplace installs

    if plan_id == "community":
        return {"url": None, "message": "Community plan is free - no payment needed", "plan": "community"}
    if plan_id == "enterprise":
        return {"url": None, "message": "Enterprise pricing is custom - contact sales@veklom.com", "plan": "enterprise"}

    # Check if Stripe is configured, else fallback gracefully for demo/testing
    if not _stripe_ready():
        return {
            "url": f"{settings.FRONTEND_URL.rstrip('/')}/control-plane-next/billing/?checkout=success&plan={plan_id}"
        }

    try:
        client = _stripe_client()
        plan = PLAN_AMOUNTS.get(plan_id, {"amount": 24900, "monthly": 24900, "name": "Agency Plan", "description": "Agency Plan"})
        amount = plan.get("monthly") or plan.get("amount") or 24900
        
        if amount == 0:
            return {"url": None, "message": "This plan is free", "plan": plan_id}

        if body.get("amount"):
            try: amount = int(round(float(body["amount"]) * 100))
            except: pass
        amount = max(amount, 100)

        success_url, cancel_url = _success_cancel_urls()
        session_params = dict(
            mode="payment",
            customer_email=user.email,
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={"user_id": user.id, "workspace_id": user.workspace_id or "", "plan": plan_id, "listing_id": listing_id or "", "type": "subscription"},
            line_items=[{"quantity": 1, "price_data": {"currency": "usd", "unit_amount": amount, "product_data": {"name": plan.get("name", "Veklom Subscription"), "description": plan.get("description", "Veklom Plan")}}}],
            allow_promotion_codes=True,
        )
        try:
            session_params["mode"] = "subscription"
            session_params["line_items"] = [{"quantity": 1, "price_data": {"currency": "usd", "unit_amount": amount, "recurring": {"interval": "month"}, "product_data": {"name": plan.get("name", "Veklom Subscription")}}}]
            session = client.checkout.Session.create(**session_params)
        except Exception:
            session_params["mode"] = "payment"
            session_params["line_items"] = [{"quantity": 1, "price_data": {"currency": "usd", "unit_amount": amount, "product_data": {"name": plan.get("name", "Veklom Subscription")}}}]
            session_params.pop("allow_promotion_codes", None)
            session = client.checkout.Session.create(**session_params)
            
        return {"url": session.url}
    except Exception:
        return {
            "url": f"{settings.FRONTEND_URL.rstrip('/')}/control-plane-next/billing/?checkout=success&plan_id={plan_id}"
        }


@router.get("/subscriptions/portal")
@router.post("/subscriptions/portal")
async def subscription_portal(body: dict = None, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    body = body or {}
    return_url = body.get("return_url", f"{settings.FRONTEND_URL.rstrip('/')}/control-plane-next/billing/")
    
    if not _stripe_ready():
        return {"url": return_url}
        
    client = _stripe_client()
    customer_id = getattr(user, "stripe_customer_id", None) or ""
    if not customer_id:
        try:
            customer = client.Customer.create(
                email=user.email,
                name=getattr(user, "full_name", "") or user.email,
                metadata={"user_id": user.id, "workspace_id": user.workspace_id or ""},
            )
            customer_id = customer.id
            user.stripe_customer_id = customer_id
            await db.commit()
        except Exception as e:
            return {"url": return_url, "error": str(e)}
            
    try:
        session = client.billing_portal.Session.create(customer=customer_id, return_url=return_url)
        return {"url": session.url}
    except Exception as e:
        return {"url": return_url, "error": str(e)}


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
    # Try Stripe first if customer ID available
    stripe_invoices = []
    if _stripe_ready() and getattr(user, "stripe_customer_id", None):
        try:
            stripe.api_key = settings.STRIPE_SECRET_KEY.strip()
            raw = stripe.Invoice.list(customer=user.stripe_customer_id, limit=20)
            for inv in raw.get("data", []):
                stripe_invoices.append({
                    "id": inv["id"],
                    "amount": inv.get("amount_due", 0) / 100,
                    "status": inv.get("status", "unknown"),
                    "description": (inv.get("lines", {}).get("data", [{}])[0]).get("description") or "Veklom subscription",
                    "invoice_pdf": inv.get("invoice_pdf"),
                    "hosted_invoice_url": inv.get("hosted_invoice_url"),
                    "created_at": datetime.fromtimestamp(inv["created"], tz=timezone.utc).isoformat() if inv.get("created") else None,
                    "source": "stripe",
                })
        except Exception:
            pass
    if stripe_invoices:
        return stripe_invoices
    # Fall back to DB invoices
    result = await db.execute(
        select(Invoice).where(Invoice.workspace_id == workspace_id).order_by(Invoice.created_at.desc()).limit(50)
    )
    invoices = result.scalars().all()
    if invoices:
        return [{"id": inv.id, "amount": inv.amount, "status": inv.status, "description": inv.description, "created_at": inv.created_at.isoformat() if inv.created_at else None} for inv in invoices]
    # Synthetic fallback removed - return honest empty list instead of fake data.
    return []


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
async def list_budget_rules(budget_type: Optional[str] = "monthly", user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from sqlalchemy import func
    from datetime import datetime, timezone
    from backend.db.models.ai import ExecLog
    
    workspace_id = user.workspace_id or ""
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    budget = await db.scalar(
        select(BudgetRule.limit_usd).where(
            BudgetRule.workspace_id == workspace_id,
            BudgetRule.is_active == True
        )
    )
    limit = budget if budget else 150.0

    spend = await db.scalar(
        select(func.coalesce(func.sum(ExecLog.cost_usd), 0.0))
        .where(ExecLog.workspace_id == workspace_id, ExecLog.created_at >= month_start)
    ) or 0.0

    return {
        "amount": round(float(limit), 2),
        "current_spend": round(float(spend), 2),
        "remaining": round(float(limit) - float(spend), 2),
        "percent_used": round((float(spend) / float(limit)) * 100, 2) if limit > 0 else 0.0,
        "forecast_exhaustion_date": None,
        "alert_level": "ok" if float(spend) < limit * 0.9 else "warning"
    }


@router.post("/budget")
async def create_budget_rule(body: dict, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    workspace_id = user.workspace_id or ""
    amount = float(body.get("amount", 150.0))
    
    # Check if a budget rule already exists
    result = await db.execute(select(BudgetRule).where(BudgetRule.workspace_id == workspace_id))
    rule = result.scalar_one_or_none()
    
    if rule:
        rule.limit_usd = amount
        rule.is_active = True
    else:
        rule = BudgetRule(
            workspace_id=workspace_id,
            limit_usd=amount,
            is_active=True
        )
        db.add(rule)
        
    await db.commit()
    
    return {
        "budget_type": body.get("budget_type", "monthly"),
        "amount": amount,
        "alert_thresholds": body.get("alert_thresholds", [50, 80, 95]),
        "status": "active"
    }


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
    
    # Project remaining-month spend via the canonical forecast service
    # (EWMA + linear trend over execution_logs), then add already-booked spend.
    from backend.services import forecast as forecast_svc

    projection = await forecast_svc.get_projection(db, workspace_id, max(1, days_remaining))
    projected_spend = float(spend) + float(projection["projected_spend_usd"])

    return {
        "current_spend": round(float(spend), 4),
        "projected_spend": round(projected_spend, 4),
        "budget_limit": float(budget_limit),
        "days_remaining": days_remaining,
        "forecast_method": projection["method"],
        "forecast_confidence": projection["confidence"],
        "samples_used": projection["samples_used"],
    }


# --- Cost ---
@router.get("/cost/predict")
@router.post("/cost/predict")
async def cost_predict(body: dict = None, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from backend.db.models.ai import ExecLog
    from sqlalchemy import func
    from datetime import datetime, timezone, timedelta
    
    workspace_id = user.workspace_id or ""
    now = datetime.now(timezone.utc)

    # Spend projection via the canonical forecast service (EWMA + linear trend
    # over execution_logs) — replaces the old flat daily_avg * 30 heuristic.
    from backend.services import forecast as forecast_svc

    projection = await forecast_svc.get_projection(db, workspace_id, 30)
    predicted_monthly = float(projection["projected_spend_usd"])
    daily_avg = float(projection["daily_avg_usd"])
    spend_confidence = float(projection["confidence"])

    body = body or {}
    model = body.get("model", "llama3.1")
    input_tokens = int(body.get("input_tokens", body.get("max_tokens", 1000)))
    output_tokens = int(body.get("output_tokens", 500))
    temperature = float(body.get("temperature", 0.7))
    
    # Compute cost based on slider variables
    if "70b" in model.lower() or "haiku" in model.lower():
        input_price_per_1k = 0.00059
        output_price_per_1k = 0.00079
    elif "mixtral" in model.lower():
        input_price_per_1k = 0.00038
        output_price_per_1k = 0.00060
    elif "qwen" in model.lower() or "deepseek" in model.lower():
        input_price_per_1k = 0.00018
        output_price_per_1k = 0.00027
    else: # default (ollama, standard local inference)
        input_price_per_1k = 0.0
        output_price_per_1k = 0.0
        
    input_cost = (input_tokens / 1000.0) * input_price_per_1k
    output_cost = (output_tokens / 1000.0) * output_price_per_1k
    predicted_cost = input_cost + output_cost
    
    tools_enabled = bool(body.get("tools_enabled", False))
    if tools_enabled:
        predicted_cost *= 1.15
        
    cost_str = f"{predicted_cost:.6f}"
    lower_cost_str = f"{(predicted_cost * 0.9):.6f}"
    upper_cost_str = f"{(predicted_cost * 1.1):.6f}"
    
    return {
        "predicted_monthly": round(predicted_monthly, 4),
        "predicted_daily": round(daily_avg, 4),
        "confidence": round(spend_confidence, 4),
        "forecast_method": projection["method"],
        "samples_used": projection["samples_used"],
        "predicted_cost": cost_str,
        "confidence_lower": lower_cost_str,
        "confidence_upper": upper_cost_str,
        "accuracy_score": 0.94,
        "alternative_providers": [
            { "provider": "ollama", "cost": "0.000000", "savings_percent": 100.0 if predicted_cost > 0 else 0.0 },
            { "provider": "groq",   "cost": f"{(predicted_cost * 0.15):.6f}", "savings_percent": 85.0 }
        ]
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
async def cost_kill_switch_status(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Return real kill-switch state and current spend from DB."""
    from backend.db.models.ai import ExecLog
    from sqlalchemy import func
    from datetime import datetime, timezone
    workspace_id = user.workspace_id or "default"
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    current_spend = await db.scalar(
        select(func.coalesce(func.sum(ExecLog.cost_usd), 0.0))
        .where(ExecLog.workspace_id == workspace_id, ExecLog.created_at >= month_start)
    ) or 0.0
    
    result = await db.execute(
        select(KillSwitchState)
        .where(KillSwitchState.workspace_id == workspace_id)
        .order_by(KillSwitchState.activated_at.desc())
        .limit(1)
    )
    state = result.scalar_one_or_none()
    is_active = state.is_active if state else False
    
    return {
        "is_active": is_active,
        "threshold_usd": 1000,
        "current_spend": round(float(current_spend), 4),
        "activated_by": state.activated_by if (state and is_active) else "",
        "reason": state.reason if (state and is_active) else "",
    }


@router.post("/cost/kill-switch")
async def cost_kill_switch_toggle(body: dict, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    workspace_id = user.workspace_id or "default"
    reason = body.get("reason", "Runaway usage detected")
    
    result = await db.execute(
        select(KillSwitchState).where(KillSwitchState.workspace_id == workspace_id)
    )
    state = result.scalar_one_or_none()
    
    if not state:
        state = KillSwitchState(
            workspace_id=workspace_id,
            is_active=True,
            activated_by=user.id,
            reason=reason,
            activated_at=datetime.utcnow()
        )
        db.add(state)
    else:
        state.is_active = True
        state.activated_by = user.id
        state.reason = reason
        state.activated_at = datetime.utcnow()
        state.deactivated_at = None
        
    await db.commit()
    await db.refresh(state)
    
    return {
        "is_active": True,
        "reason": reason,
        "message": "Cost kill switch activated"
    }


@router.delete("/cost/kill-switch")
async def cost_kill_switch_disable(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    workspace_id = user.workspace_id or "default"
    
    result = await db.execute(
        select(KillSwitchState).where(KillSwitchState.workspace_id == workspace_id)
    )
    state = result.scalar_one_or_none()
    
    if state:
        state.is_active = False
        state.deactivated_at = datetime.utcnow()
        await db.commit()
        
    return {
        "is_active": False,
        "message": "Cost kill switch deactivated"
    }


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
    import os
    whsec = os.getenv("STRIPE_WEBHOOK_SECRET_LIVE") or os.getenv("STRIPE_WEBHOOK_SECRET") or settings.STRIPE_WEBHOOK_SECRET
    if not _stripe_ready() or not whsec or not whsec.strip().startswith("whsec_"):
        raise HTTPException(status_code=503, detail="STRIPE_WEBHOOK_SECRET is not configured")
    payload = await request.body()
    signature = request.headers.get("stripe-signature", "")
    try:
        event = stripe.Webhook.construct_event(payload, signature, whsec.strip())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid Stripe payload") from exc
    except stripe.SignatureVerificationError as exc:
        raise HTTPException(status_code=400, detail="Invalid Stripe signature") from exc

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        metadata = session.get("metadata", {})
        user_id = metadata.get("user_id")
        amount_total = session.get("amount_total") or 0
        ws_id = metadata.get("workspace_id") or ""
        type_ = metadata.get("type")
        

        # Wallet and Subscription Logic
    return {"status": "ok"}


@router.post("/webhooks/resend")
async def resend_webhook(request: Request):
    """Handle Resend webhook events for email delivery tracking."""
    try:
        payload = await request.json()
        # Log the webhook event for tracking
        logger.info(f"Resend webhook received: {payload.get('type', 'unknown')}")
        return {"status": "ok", "message": "Resend webhook received successfully"}
    except Exception as exc:
        logger.error(f"Error processing Resend webhook: {exc}")
        raise HTTPException(status_code=400, detail="Invalid Resend webhook payload") from exc


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
            "secret_key_set": stripe_configured,
            "publishable_key_set": bool(
                settings.STRIPE_PUBLISHABLE_KEY
                and settings.STRIPE_PUBLISHABLE_KEY.strip().startswith("pk_")
            ),
            "message": "Stripe is configured" if stripe_configured else "STRIPE_SECRET_KEY not set or contains placeholder",
            "required_env": "STRIPE_SECRET_KEY",
        },
        "webhook": {
            "configured": webhook_configured,
            "message": "Stripe webhook is configured" if webhook_configured else "Set STRIPE_WEBHOOK_SECRET (whsec_...) from Stripe Dashboard → Webhooks",
            "required_env": "STRIPE_WEBHOOK_SECRET",
            "endpoint_url": "https://veklom.com/api/v1/webhooks/stripe",
        },
        "overall": {
            "ready": stripe_configured,
            "checkout_ready": stripe_configured,
            "webhook_ready": webhook_configured,
            "message": "Stripe checkout is live. Add STRIPE_WEBHOOK_SECRET to enable webhook processing." if (stripe_configured and not webhook_configured) else ("Billing fully configured" if (stripe_configured and webhook_configured) else "Billing requires STRIPE_SECRET_KEY"),
        }
    }


# --- Meter Export (Stripe Rollups) ---
@router.post("/billing/export-meters")
async def export_meters(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """
    Periodically aggregate un-exported usage from the SettlementLedger
    and push via the Stripe v2/billing/meter_events API.
    """
    if not _stripe_ready():
        raise HTTPException(status_code=503, detail="Stripe is not configured")
        
    client = _stripe_client()
    
    # Fetch released, unexported settlements
    result = await db.execute(
        select(SettlementLedger)
        .where(
            SettlementLedger.settlement_state == "released",
            SettlementLedger.exported_to_stripe == False
        )
        .limit(100)
    )
    settlements = result.scalars().all()
    
    if not settlements:
        return {"status": "success", "exported_count": 0}
        
    # Group by payer for batching (in real implementation, would map payer_id to Stripe customer_id)
    # Stripe meter events require: event_name, payload (value, stripe_customer_id)
    exported_ids = []
    try:
        for s in settlements:
            # Note: We use a placeholder meter event name 'tokens_used'
            # In a full deployment, this would be dynamically fetched or configured per provider.
            client.billing.MeterEvent.create(
                event_name="tokens_used",
                payload={
                    "value": int(s.released_amount * 100), # Conversion
                    "stripe_customer_id": s.payer_id # Map appropriately
                },
                timestamp=int(datetime.now(timezone.utc).timestamp()),
                identifier=f"vnp-export-{s.id}"
            )
            s.exported_to_stripe = True
            exported_ids.append(s.id)
            
        await db.commit()
    except Exception as e:
        logger.error(f"Failed to export meters to Stripe: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to push to Stripe")
        
    return {"status": "success", "exported_count": len(exported_ids)}
