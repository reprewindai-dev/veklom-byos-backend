"""Agentic Commerce — sell EVERY Veklom revenue stream through AI agents.

A spec-aligned subset of the open Agentic Commerce Protocol (ACP,
agenticcommerce.dev) plus a Stripe Agentic Commerce Suite (ACS) catalog feed,
unified across all four ways Veklom earns:

  1. marketplace      — sovereign/compliance packs, connectors (Stripe)
  2. governed_service — x402 per-call governed runs, USDC on Base (x402) or prepaid
  3. subscription     — Growth / Sovereign plans (Stripe)
  4. wallet_credit    — prepaid operating-reserve credit packs (Stripe)

  Discovery (public)
    GET  /agentic_commerce/product_feed          unified ACP JSON product feed
    GET  /agentic_commerce/feed.csv              ACS catalog feed (CSV)

  Agentic checkout (agent-authenticated via JWT or X-API-Key)
    POST /agentic_commerce/checkout_sessions                 create
    GET  /agentic_commerce/checkout_sessions/{id}            retrieve
    POST /agentic_commerce/checkout_sessions/{id}            update
    POST /agentic_commerce/checkout_sessions/{id}/complete   complete + pay
    POST /agentic_commerce/checkout_sessions/{id}/cancel     cancel

On completion each line item is fulfilled into the SAME effects the Stripe
webhook already produces: marketplace -> InstalledAsset, subscription ->
Subscription, wallet_credit / prepaid governed_service -> WalletTransaction
top-up. Per-call governed runs are ALSO directly payable in USDC on Base via
the x402 metadata advertised in the feed (see /.well-known/x402.json).
"""

import csv
import io
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.apps.api.routers.billing import PLAN_AMOUNTS
from backend.core.config.settings import settings
from backend.core.database.database import get_db
from backend.core.middleware.x402 import VEKLOM_USDC_ADDR
from backend.apps.api.routers.discovery import VEKLOM_TREASURY
from backend.core.middleware.x402 import VEKLOM_TREASURY, VEKLOM_USDC_ADDR
from backend.core.security.auth import get_current_user_or_api_key
from backend.db.models.agentic_commerce import AgenticCheckoutSession
from backend.db.models.billing import Subscription, WalletTransaction
from backend.db.models.marketplace import InstalledAsset, MarketplaceListing

router = APIRouter(tags=["Agentic Commerce"])

_API_VERSION = "2026-04-22.preview"
_SITE = (settings.FRONTEND_URL.rstrip("/") if getattr(settings, "FRONTEND_URL", "") else "") or "https://veklom.com"

# Prepaid operating-reserve credit packs (USD). Funds x402 governed usage.
_CREDIT_PACKS = (50, 100, 250, 500)

# Product types sold through the agentic storefront.
_PT_MARKETPLACE = "marketplace"
_PT_GOVERNED = "governed_service"
_PT_SUBSCRIPTION = "subscription"
_PT_CREDIT = "wallet_credit"

# Governed-run catalogue — mirrors backend.core.middleware.x402._PAID_ROUTES.
# Kept here (with billing units) so the storefront is self-contained.
_GOVERNED_CATALOG: dict[str, dict] = {
    "ai_inference":        {"price_usdc": 0.008, "unit": "per request", "name": "AI Inference",         "path": "/api/v1/ai/inference",        "free_daily": 5},
    "ai_chat":             {"price_usdc": 0.005, "unit": "per request", "name": "AI Chat Completion",   "path": "/api/v1/ai/chat",             "free_daily": 5},
    "gpc_compile":         {"price_usdc": 0.015, "unit": "per compile", "name": "GPC Governed Compile", "path": "/api/v1/gpc/compile",         "free_daily": 3},
    "gpc_intent_to_plan":  {"price_usdc": 0.010, "unit": "per plan",    "name": "GPC Intent-to-Plan",   "path": "/api/v1/gpc/intent-to-plan",  "free_daily": 3},
    "gpc_run":             {"price_usdc": 0.020, "unit": "per run",     "name": "GPC Plan Execution",   "path": "/api/v1/gpc/runs",            "free_daily": 0},
    "pipeline_trigger":    {"price_usdc": 0.025, "unit": "per trigger", "name": "Pipeline Trigger",     "path": "/api/v1/pipelines/trigger",   "free_daily": 0},
    "runtime_job":         {"price_usdc": 0.020, "unit": "per job",     "name": "Runtime Job",          "path": "/api/v1/runtime/jobs",        "free_daily": 0},
    "evidence_export":     {"price_usdc": 0.005, "unit": "per export",  "name": "Evidence Export",      "path": "/api/v1/evidence/export",     "free_daily": 2},
    "compliance_report":   {"price_usdc": 0.010, "unit": "per report",  "name": "Compliance Report",    "path": "/api/v1/compliance/report",   "free_daily": 1},
    "marketplace_acquire": {"price_usdc": 0.050, "unit": "per acquire", "name": "Marketplace Acquire",  "path": "/api/v1/marketplace/acquire", "free_daily": 0},
    "audit_verify":        {"price_usdc": 0.003, "unit": "per verify",  "name": "Audit Verification",   "path": "/api/v1/audit/verify",        "free_daily": 5},
}

# ACP/ACS checkout-session lifecycle states.
_NOT_READY = "not_ready_for_payment"
_READY = "ready_for_payment"
_COMPLETED = "completed"
_CANCELED = "canceled"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _to_minor(amount_usd) -> int:
    """USD (major units, may be float) -> integer minor units (cents)."""
    try:
        return int(round(float(amount_usd or 0) * 100))
    except (TypeError, ValueError):
        return 0


def _x402_block(price_usdc: float, name: str) -> dict:
    return {
        "scheme": "exact",
        "network": "base",
        "asset": VEKLOM_USDC_ADDR,
        "pay_to": str(VEKLOM_TREASURY),
        "amount_micro_usdc": int(round(float(price_usdc) * 1_000_000)),
        "max_timeout_seconds": 300,
        "config_url": f"{_SITE}/.well-known/x402.json",
        "description": f"Veklom {name} — governed AI execution, pay-per-call in USDC on Base",
    }


# --- per-product-type feed builders ---------------------------------------
def _marketplace_item(listing: MarketplaceListing) -> dict:
    cfg = listing.config_json or {}
    price_minor = _to_minor(listing.price)
    recurring = (listing.pricing_model or "").lower() in ("monthly", "yearly", "subscription")
    return {
        "id": listing.id,
        "product_type": _PT_MARKETPLACE,
        "title": listing.name,
        "description": (cfg.get("long_description") or listing.description or listing.name)[:5000],
        "link": f"{_SITE}/control-plane-next/marketplace/",
        "image_link": cfg.get("icon_url") or listing.icon_url or "",
        "price": {"amount": price_minor, "currency": "usd"},
        "availability": "in_stock" if listing.status == "published" else "out_of_stock",
        "brand": cfg.get("vendor_name", "Veklom"),
        "product_category": listing.category,
        "pricing_model": listing.pricing_model,
        "recurring": recurring,
        "payment_rails": ["stripe"],
        "tags": listing.tags or [],
        "rating": listing.rating,
        "enable_checkout": price_minor == 0 or listing.status == "published",
    }


def _governed_items() -> list[dict]:
    items = []
    for key, c in _GOVERNED_CATALOG.items():
        items.append({
            "id": f"svc_{key}",
            "product_type": _PT_GOVERNED,
            "title": c["name"],
            "description": f"Governed {c['name']} — billed {c['unit']}. Pay per call in USDC on Base via x402, or prepay reserve credits.",
            "link": f"{_SITE}{c['path']}",
            "price": {"amount": _to_minor(c["price_usdc"]), "currency": "usd", "usdc": c["price_usdc"]},
            "unit": c["unit"],
            "api_path": c["path"],
            "free_daily": c["free_daily"],
            "availability": "in_stock",
            "product_category": "governed_run",
            "recurring": False,
            "payment_rails": ["x402_usdc", "stripe_credits"],
            "x402": _x402_block(c["price_usdc"], c["name"]),
            "enable_checkout": True,
        })
    return items


def _subscription_items() -> list[dict]:
    items = []
    for key, plan in PLAN_AMOUNTS.items():
        amount = plan.get("monthly") or plan.get("amount") or 0
        if amount <= 0:
            continue  # community / enterprise (custom) — not directly checkout-able
        items.append({
            "id": f"plan_{key}",
            "product_type": _PT_SUBSCRIPTION,
            "title": plan["name"],
            "description": plan.get("description", plan["name"]),
            "link": f"{_SITE}/control-plane-next/billing/",
            "price": {"amount": amount, "currency": "usd"},
            "availability": "in_stock",
            "product_category": "subscription",
            "recurring": True,
            "interval": "month",
            "plan_key": key,
            "payment_rails": ["stripe"],
            "enable_checkout": True,
        })
    return items


def _credit_items() -> list[dict]:
    items = []
    for amt in _CREDIT_PACKS:
        items.append({
            "id": f"credit_{amt}",
            "product_type": _PT_CREDIT,
            "title": f"${amt} Operating Reserve Credit",
            "description": f"Prepay ${amt} of Veklom operating reserve. Funds governed (x402) usage on your workspace.",
            "link": f"{_SITE}/control-plane-next/billing/",
            "price": {"amount": amt * 100, "currency": "usd"},
            "availability": "in_stock",
            "product_category": "reserve_credit",
            "recurring": False,
            "credit_usd": amt,
            "payment_rails": ["stripe"],
            "enable_checkout": True,
        })
    return items


async def _published(db: AsyncSession) -> list[MarketplaceListing]:
    from backend.apps.api.routers.marketplace import _ensure_catalog_seeded
    await _ensure_catalog_seeded(db)
    result = await db.execute(
        select(MarketplaceListing).where(MarketplaceListing.status == "published").limit(200)
    )
    return list(result.scalars().all())


# --- checkout line-item resolution ----------------------------------------
async def _resolve_item(db: AsyncSession, product_type: str, item_id: str) -> dict:
    """Resolve a requested product into {id, name, product_type, unit_minor, meta}."""
    pt = (product_type or _PT_MARKETPLACE).lower()

    if pt == _PT_GOVERNED:
        key = item_id[4:] if item_id.startswith("svc_") else item_id
        c = _GOVERNED_CATALOG.get(key)
        if not c:
            raise HTTPException(status_code=404, detail=f"Governed service '{item_id}' not found")
        return {"id": f"svc_{key}", "name": c["name"], "product_type": pt,
                "unit_minor": _to_minor(c["price_usdc"]), "meta": {"service_key": key, "path": c["path"]}}

    if pt == _PT_SUBSCRIPTION:
        key = item_id[5:] if item_id.startswith("plan_") else item_id
        plan = PLAN_AMOUNTS.get(key)
        if not plan or (plan.get("monthly") or plan.get("amount") or 0) <= 0:
            raise HTTPException(status_code=404, detail=f"Subscription plan '{item_id}' not available")
        amount = plan.get("monthly") or plan.get("amount")
        return {"id": f"plan_{key}", "name": plan["name"], "product_type": pt,
                "unit_minor": int(amount), "meta": {"plan_key": key}}

    if pt == _PT_CREDIT:
        # credit_<amount> or a raw amount.
        raw = item_id[7:] if item_id.startswith("credit_") else item_id
        try:
            amt = int(float(raw))
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail=f"Invalid credit pack '{item_id}'")
        if amt < 1:
            raise HTTPException(status_code=400, detail="Credit amount must be >= $1")
        return {"id": f"credit_{amt}", "name": f"${amt} Operating Reserve Credit", "product_type": pt,
                "unit_minor": amt * 100, "meta": {"credit_usd": amt}}

    # default: marketplace listing
    from backend.apps.api.routers.marketplace import normalize_listing_id, _ensure_catalog_seeded
    await _ensure_catalog_seeded(db)
    norm = normalize_listing_id(item_id)
    listing = (await db.execute(
        select(MarketplaceListing).where(MarketplaceListing.id == norm)
    )).scalars().first()
    if not listing:
        raise HTTPException(status_code=404, detail=f"Listing '{item_id}' not found")
    return {"id": listing.id, "name": listing.name, "product_type": _PT_MARKETPLACE,
            "unit_minor": _to_minor(listing.price), "meta": {"listing_id": listing.id}}


def _build_line_items(resolved: list[dict]) -> tuple[list[dict], int]:
    line_items, subtotal = [], 0
    for r in resolved:
        qty = max(1, int(r.get("quantity", 1)))
        unit = r["unit_minor"]
        line_total = unit * qty
        subtotal += line_total
        line_items.append({
            "id": f"li_{r['id']}",
            "item": {"id": r["id"], "quantity": qty},
            "name": r["name"],
            "product_type": r["product_type"],
            "meta": r.get("meta", {}),
            "base_amount": unit,
            "subtotal": line_total,
            "tax": 0,
            "total": line_total,
        })
    return line_items, subtotal


def _totals(subtotal: int) -> list[dict]:
    return [
        {"type": "items_base_amount", "display_text": "Items", "amount": subtotal},
        {"type": "subtotal", "display_text": "Subtotal", "amount": subtotal},
        {"type": "total", "display_text": "Total", "amount": subtotal},
    ]


def _session_view(row: AgenticCheckoutSession) -> dict:
    data = dict(row.data_json or {})
    data["id"] = row.id
    data["status"] = row.status
    data["currency"] = row.currency
    if row.order_id:
        data.setdefault("order", {})
        data["order"]["id"] = row.order_id
        data["order"]["checkout_session_id"] = row.id
    return data


# ---------------------------------------------------------------------------
# Discovery — unified public product feed
# ---------------------------------------------------------------------------
@router.get("/agentic_commerce/product_feed")
async def product_feed(db: AsyncSession = Depends(get_db)):
    """Unified ACP JSON feed across every Veklom revenue rail (public)."""
    marketplace = [_marketplace_item(l) for l in await _published(db)]
    governed = _governed_items()
    subs = _subscription_items()
    credits = _credit_items()
    products = marketplace + governed + subs + credits
    return {
        "object": "product_feed",
        "protocol": "acp",
        "version": _API_VERSION,
        "merchant": {"name": "Veklom", "url": _SITE},
        "currency": "usd",
        "payment_rails": {
            "x402_usdc": {"network": "base", "asset": VEKLOM_USDC_ADDR, "pay_to": str(VEKLOM_TREASURY),
                          "config_url": f"{_SITE}/.well-known/x402.json"},
            "stripe": {"checkout": f"{_SITE}/api/v1/agentic_commerce/checkout_sessions"},
        },
        "count": len(products),
        "counts_by_type": {
            _PT_MARKETPLACE: len(marketplace), _PT_GOVERNED: len(governed),
            _PT_SUBSCRIPTION: len(subs), _PT_CREDIT: len(credits),
        },
        "products": products,
    }


@router.get("/agentic_commerce/feed.csv")
async def feed_csv(db: AsyncSession = Depends(get_db)):
    """Stripe ACS catalog feed (CSV) for Product Catalog Import."""
    marketplace = [_marketplace_item(l) for l in await _published(db)]
    rows = marketplace + _governed_items() + _subscription_items() + _credit_items()
    columns = [
        "id", "title", "description", "link", "image_link", "price",
        "availability", "condition", "brand", "product_category",
        "enable_search", "enable_checkout", "stripe_product_tax_code",
    ]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    for item in rows:
        price_major = (item["price"]["amount"] or 0) / 100.0
        writer.writerow({
            "id": item["id"],
            "title": item["title"],
            "description": (item["description"] or "").replace("\n", " ").strip(),
            "link": item["link"],
            "image_link": item.get("image_link", ""),
            "price": f"{price_major:.2f} USD",
            "availability": item.get("availability", "in_stock"),
            "condition": "new",
            "brand": item.get("brand", "Veklom"),
            "product_category": item.get("product_category", ""),
            "enable_search": "true",
            "enable_checkout": "true" if item.get("enable_checkout") else "false",
            "stripe_product_tax_code": "txcd_10000000",  # general — digital service
        })
    return PlainTextResponse(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="veklom-catalog-feed.csv"'},
    )


# ---------------------------------------------------------------------------
# Agentic checkout lifecycle
# ---------------------------------------------------------------------------
async def _load_session(db: AsyncSession, session_id: str) -> AgenticCheckoutSession:
    row = (await db.execute(
        select(AgenticCheckoutSession).where(AgenticCheckoutSession.id == session_id)
    )).scalars().first()
    if not row:
        raise HTTPException(status_code=404, detail="Checkout session not found")
    return row


@router.post("/agentic_commerce/checkout_sessions")
async def create_checkout_session(
    body: dict,
    user=Depends(get_current_user_or_api_key),
    db: AsyncSession = Depends(get_db),
):
    """Create an ACP checkout session across any Veklom revenue rail.

    Body: {currency?, line_item_details: [{product_type?, sku_id|item_id, quantity}], buyer?}
    product_type one of: marketplace (default), governed_service, subscription, wallet_credit.
    """
    raw_items = body.get("line_item_details") or body.get("items") or []
    if not raw_items:
        raise HTTPException(status_code=400, detail="line_item_details is required")

    resolved = []
    for it in raw_items:
        item_id = it.get("sku_id") or it.get("item_id") or it.get("id")
        if not item_id:
            raise HTTPException(status_code=400, detail="each line item needs sku_id/item_id")
        r = await _resolve_item(db, it.get("product_type"), item_id)
        r["quantity"] = it.get("quantity", 1)
        resolved.append(r)

    line_items, subtotal = _build_line_items(resolved)
    currency = (body.get("currency") or "usd").lower()
    buyer = body.get("buyer") or {}
    session_id = f"acs_{uuid.uuid4().hex[:24]}"

    data = {
        "id": session_id,
        "object": "checkout_session",
        "protocol": "acp",
        "status": _READY,
        "currency": currency,
        "line_items": line_items,
        "fulfillment_type": "digital",
        "fulfillment_options": [{
            "type": "digital", "id": "digital_instant",
            "display_text": "Instant activation in your Veklom workspace", "amount": 0,
        }],
        "totals": _totals(subtotal),
        "messages": [],
        "links": [{"type": "terms_of_service", "url": f"{_SITE}/terms"}],
        "payment_provider": {"provider": "stripe", "supported_payment_methods": ["card"]},
        "buyer": buyer,
    }

    row = AgenticCheckoutSession(
        id=session_id,
        workspace_id=getattr(user, "workspace_id", "") or "",
        buyer_email=buyer.get("email") or getattr(user, "email", "") or "",
        agent_id=str(getattr(user, "id", "") or ""),
        status=_READY,
        currency=currency,
        amount_total=subtotal,
        data_json=data,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return _session_view(row)


@router.get("/agentic_commerce/checkout_sessions/{session_id}")
async def get_checkout_session(
    session_id: str,
    user=Depends(get_current_user_or_api_key),
    db: AsyncSession = Depends(get_db),
):
    return _session_view(await _load_session(db, session_id))


@router.post("/agentic_commerce/checkout_sessions/{session_id}")
async def update_checkout_session(
    session_id: str,
    body: dict,
    user=Depends(get_current_user_or_api_key),
    db: AsyncSession = Depends(get_db),
):
    """Update buyer details on an in-progress session."""
    row = await _load_session(db, session_id)
    if row.status in (_COMPLETED, _CANCELED):
        raise HTTPException(status_code=409, detail=f"Session is {row.status}")
    data = dict(row.data_json or {})
    if isinstance(body.get("buyer"), dict):
        data["buyer"] = {**(data.get("buyer") or {}), **body["buyer"]}
        if body["buyer"].get("email"):
            row.buyer_email = body["buyer"]["email"]
    row.data_json = data
    await db.commit()
    await db.refresh(row)
    return _session_view(row)


@router.post("/agentic_commerce/checkout_sessions/{session_id}/cancel")
async def cancel_checkout_session(
    session_id: str,
    user=Depends(get_current_user_or_api_key),
    db: AsyncSession = Depends(get_db),
):
    row = await _load_session(db, session_id)
    if row.status == _COMPLETED:
        raise HTTPException(status_code=409, detail="Completed session cannot be canceled")
    row.status = _CANCELED
    await db.commit()
    await db.refresh(row)
    return _session_view(row)


# --- fulfillment dispatch --------------------------------------------------
async def _fulfill(db: AsyncSession, row: AgenticCheckoutSession, line_items: list[dict]) -> list[str]:
    """Fulfill each line item into its real backend effect. Returns notes."""
    notes = []
    workspace_id = row.workspace_id or ""
    user_id = row.agent_id or "agent"

    for li in line_items:
        pt = li.get("product_type", _PT_MARKETPLACE)
        meta = li.get("meta") or {}
        line_usd = (li.get("total") or 0) / 100.0

        if pt == _PT_MARKETPLACE:
            listing_id = meta.get("listing_id") or (li.get("item") or {}).get("id")
            if workspace_id and listing_id:
                await _install_listing(db, workspace_id, user_id, listing_id)
                notes.append(f"installed:{listing_id}")

        elif pt == _PT_SUBSCRIPTION:
            await _activate_subscription(db, workspace_id, user_id, meta.get("plan_key", "growth"))
            notes.append(f"subscribed:{meta.get('plan_key')}")

        elif pt in (_PT_CREDIT, _PT_GOVERNED):
            # Prepaid reserve / governed bundle -> wallet top-up that funds x402 usage.
            if user_id:
                db.add(WalletTransaction(
                    user_id=user_id,
                    workspace_id=workspace_id,
                    amount=line_usd,
                    tx_type="topup",
                    description=f"Agentic purchase: {li.get('name')}",
                    reference_id=row.id,
                ))
                notes.append(f"credited:{line_usd:.2f}")

    return notes


async def _install_listing(db: AsyncSession, workspace_id: str, installed_by: str, listing_id: str) -> None:
    listing = (await db.execute(
        select(MarketplaceListing).where(MarketplaceListing.id == listing_id)
    )).scalars().first()
    if not listing:
        return
    exists = (await db.execute(
        select(InstalledAsset).where(
            InstalledAsset.workspace_id == workspace_id,
            InstalledAsset.listing_id == listing_id,
        )
    )).scalars().first()
    if exists:
        return
    db.add(InstalledAsset(
        id=str(uuid.uuid4()),
        workspace_id=workspace_id,
        listing_id=listing_id,
        installed_by=installed_by or "agent",
        asset_type=listing.category,
        name=listing.name,
        status="active",
        config_json=listing.config_json or {},
        version="1.0.0",
    ))
    listing.downloads = (listing.downloads or 0) + 1


async def _activate_subscription(db: AsyncSession, workspace_id: str, user_id: str, plan_key: str) -> None:
    if not workspace_id:
        return
    existing = (await db.execute(
        select(Subscription).where(Subscription.workspace_id == workspace_id)
        .order_by(Subscription.created_at.desc()).limit(1)
    )).scalar_one_or_none()
    end = datetime.now(timezone.utc) + timedelta(days=30)
    if existing:
        existing.plan = plan_key
        existing.status = "active"
        existing.current_period_end = end
    else:
        db.add(Subscription(
            user_id=user_id or "agent",
            workspace_id=workspace_id,
            plan=plan_key,
            status="active",
            current_period_start=datetime.now(timezone.utc),
            current_period_end=end,
            activation_fee_paid=True,
        ))


@router.post("/agentic_commerce/checkout_sessions/{session_id}/complete")
async def complete_checkout_session(
    session_id: str,
    body: dict = None,
    user=Depends(get_current_user_or_api_key),
    db: AsyncSession = Depends(get_db),
    idempotency_key: str = Header(default="", alias="Idempotency-Key"),
):
    """Complete the checkout: capture the delegated payment, then fulfill.

    Body: {payment_data: {token, provider, billing_address}, buyer?}
    Free items complete without a charge. When a Stripe delegated/shared
    payment token is supplied and Stripe is configured, a PaymentIntent is
    created to capture the total. Completion is idempotent.
    """
    body = body or {}
    row = await _load_session(db, session_id)

    if row.status == _COMPLETED:
        return _session_view(row)  # idempotent
    if row.status == _CANCELED:
        raise HTTPException(status_code=409, detail="Session was canceled")

    data = dict(row.data_json or {})
    line_items = data.get("line_items", [])
    total = row.amount_total or 0
    token = (body.get("payment_data") or {}).get("token")
    messages = list(data.get("messages") or [])
    payment_intent_id = ""

    if total > 0:
        from backend.apps.api.routers.billing import _stripe_ready, _stripe_client
        if token and _stripe_ready():
            try:
                client = _stripe_client()
                intent = client.PaymentIntent.create(
                    amount=total,
                    currency=row.currency,
                    shared_payment_granted_token=token,
                    confirm=True,
                    metadata={
                        "source": "agentic_commerce",
                        "checkout_session_id": session_id,
                        "workspace_id": row.workspace_id or "",
                    },
                )
                payment_intent_id = getattr(intent, "id", "") or ""
            except Exception as e:  # noqa: BLE001 — surface as ACP message, don't 500
                messages.append({"type": "error", "code": "payment_failed", "text": str(e)})
                data["messages"] = messages
                row.data_json = data
                await db.commit()
                raise HTTPException(status_code=402, detail=f"Payment failed: {e}")
        elif token and not _stripe_ready():
            messages.append({"type": "info", "code": "payment_simulated",
                             "text": "Stripe not configured — order recorded without capture."})
        else:
            raise HTTPException(status_code=402, detail="payment_data.token is required to complete a paid checkout")

    notes = await _fulfill(db, row, line_items)
    messages.append({"type": "info", "code": "fulfilled", "text": ", ".join(notes) or "no-op"})

    order_id = f"order_{uuid.uuid4().hex[:20]}"
    row.status = _COMPLETED
    row.order_id = order_id
    row.payment_intent_id = payment_intent_id
    data["messages"] = messages
    row.data_json = data
    await db.commit()
    await db.refresh(row)

    view = _session_view(row)
    view["payment_intent_id"] = payment_intent_id
    view["fulfillment"] = notes
    return view
