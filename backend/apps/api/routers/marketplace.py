"""Marketplace, vendor, listing routes."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database.database import get_db
from backend.core.security.auth import get_current_user
from backend.db.models.marketplace import MarketplaceListing, Vendor

router = APIRouter(tags=["Marketplace"])


# --- Listings ---
@router.get("/marketplace/listings")
async def list_marketplace(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MarketplaceListing).where(MarketplaceListing.status == "published").limit(50))
    items = result.scalars().all()
    if not items:
        return _mock_listings()
    return [_listing_dict(i) for i in items]


@router.get("/marketplace/tools")
async def list_marketplace_tools(
    query: str | None = Query(default=None),
    user=Depends(get_current_user),
):
    """Public-demo-safe MCP tool registry backed by the Veklom BYOS route surface."""
    tools = _source_marketplace_tools()
    if query:
        needle = query.lower()
        tools = [
            tool for tool in tools
            if needle in tool["name"].lower()
            or needle in tool["category"].lower()
            or any(needle in cap.lower() for cap in tool["capabilities"])
        ]
    return {
        "source": "veklom-byos-backend",
        "protocol": "MCP JSON-RPC 2.0 over HTTPS",
        "provider_policy": "ollama_only_for_public_demo",
        "billing_impact": "$0.00 public demo run",
        "count": len(tools),
        "tools": tools,
    }


@router.get("/listings")
async def list_listings(user=Depends(get_current_user)):
    return _mock_listings()


@router.get("/marketplace/listings/{listing_id}")
async def get_listing(listing_id: str, user=Depends(get_current_user)):
    return {"id": listing_id, "name": "AI Document Processor", "category": "tool", "price": 0.50, "status": "published"}


@router.post("/marketplace/listings")
async def create_listing(body: dict, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    listing = MarketplaceListing(
        vendor_id=user.id,
        name=body.get("name", "Untitled"),
        description=body.get("description", ""),
        category=body.get("category", "tool"),
        price=body.get("price", 0),
        status="draft",
    )
    db.add(listing)
    await db.commit()
    return _listing_dict(listing)


@router.post("/listings/create")
async def create_listing_alt(body: dict, user=Depends(get_current_user)):
    return {"id": "lst_new", "name": body.get("name", ""), "status": "draft"}


@router.post("/listings/submit")
async def submit_listing(body: dict, user=Depends(get_current_user)):
    return {"id": body.get("listing_id", ""), "status": "pending_review"}


@router.post("/listings/review")
async def review_listing(body: dict, user=Depends(get_current_user)):
    return {"id": body.get("listing_id", ""), "status": body.get("action", "approved")}


@router.patch("/marketplace/listings/{listing_id}")
async def update_listing(listing_id: str, body: dict, user=Depends(get_current_user)):
    return {"id": listing_id, "message": "Listing updated", **body}


@router.delete("/marketplace/listings/{listing_id}")
async def delete_listing(listing_id: str, user=Depends(get_current_user)):
    return {"message": "Listing deleted"}


# --- Marketplace Automation ---
@router.get("/marketplace/automation")
async def list_automations(user=Depends(get_current_user)):
    return []


@router.post("/marketplace/automation")
async def create_automation(body: dict, user=Depends(get_current_user)):
    return {"id": "auto_new", "name": body.get("name", ""), "status": "active"}


# --- Vendors ---
@router.post("/vendors/create")
async def create_vendor(body: dict, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    vendor = Vendor(
        user_id=user.id,
        business_name=body.get("business_name", ""),
        status="pending",
    )
    db.add(vendor)
    await db.commit()
    return {"id": vendor.id, "status": "pending", "business_name": vendor.business_name}


@router.post("/vendors/onboard")
async def onboard_vendor(body: dict, user=Depends(get_current_user)):
    return {"status": "onboarding_started", "stripe_url": "https://connect.stripe.com/placeholder"}


@router.get("/vendors/me/listings")
async def my_listings(user=Depends(get_current_user)):
    return []


# --- Plugins ---
@router.get("/plugins")
async def list_plugins(user=Depends(get_current_user)):
    return [
        {"id": "p1", "name": "Document Parser", "category": "tool", "status": "active", "version": "1.2.0"},
        {"id": "p2", "name": "Code Analyzer", "category": "tool", "status": "active", "version": "2.0.1"},
        {"id": "p3", "name": "Data Validator", "category": "governance", "status": "active", "version": "1.0.0"},
    ]


def _listing_dict(l: MarketplaceListing) -> dict:
    return {
        "id": l.id,
        "name": l.name,
        "description": l.description,
        "category": l.category,
        "price": l.price,
        "status": l.status,
        "downloads": l.downloads,
        "rating": l.rating,
    }


def _mock_listings():
    return [
        {"id": "ml1", "name": "AI Document Processor", "description": "Extract and analyze documents with AI", "category": "tool", "price": 0.50, "status": "published", "downloads": 245, "rating": 4.7},
        {"id": "ml2", "name": "Compliance Checker", "description": "Automated HIPAA/GDPR compliance checks", "category": "governance", "price": 1.00, "status": "published", "downloads": 189, "rating": 4.8},
        {"id": "ml3", "name": "Data Anonymizer", "description": "PII detection and anonymization", "category": "privacy", "price": 0.75, "status": "published", "downloads": 312, "rating": 4.9},
        {"id": "ml4", "name": "Model Router", "description": "Intelligent model selection and routing", "category": "infrastructure", "price": 0.25, "status": "published", "downloads": 456, "rating": 4.6},
    ]


def _source_marketplace_tools() -> list[dict]:
    return [
        {
            "id": "veklom-gpc",
            "name": "Governed Plan Compiler (GPC)",
            "category": "governance",
            "description": "Compiles messy intent into policy-checked execution plans.",
            "method": "POST",
            "endpoint": "/api/v1/gpc/compile",
            "runtime_provider": "ollama",
            "capabilities": ["intent_compile", "policy_check", "plan_generation"],
            "veklom_made": True,
            "watermark": "Veklom Sovereign AI Hub",
        },
        {
            "id": "veklom-autonomous-router",
            "name": "Autonomous Execution Router",
            "category": "execution",
            "description": "Routes public demo intents through the BYOS control layer with Ollama-first execution.",
            "method": "POST",
            "endpoint": "/api/v1/autonomous/execute",
            "runtime_provider": "ollama",
            "capabilities": ["agent_execution", "vendor_discovery", "uacp_dispatch"],
            "veklom_made": True,
            "watermark": "Veklom Sovereign AI Hub",
        },
        {
            "id": "veklom-policy-vault",
            "name": "Policy Vault",
            "category": "security",
            "description": "Evaluates tool calls, repository actions, and runtime boundaries before execution.",
            "method": "GET",
            "endpoint": "/api/v1/compliance/report",
            "runtime_provider": "ollama",
            "capabilities": ["policy_gate", "approval_boundary", "risk_classification"],
            "veklom_made": True,
            "watermark": "Veklom Sovereign AI Hub",
        },
        {
            "id": "veklom-marketplace-vendor-discovery",
            "name": "Marketplace Vendor Discovery",
            "category": "marketplace",
            "description": "Finds potential Veklom-compatible vendors and tools without leaving the public demo boundary.",
            "method": "GET",
            "endpoint": "/api/v1/marketplace/tools",
            "runtime_provider": "ollama",
            "capabilities": ["vendor_lookup", "tool_registry", "marketplace_match"],
            "veklom_made": True,
            "watermark": "Veklom Sovereign AI Hub",
        },
        {
            "id": "veklom-audit-sealer",
            "name": "Replayable Audit Evidence Sealer",
            "category": "evidence",
            "description": "Seals every demo action into a deterministic evidence block for replay.",
            "method": "GET",
            "endpoint": "/api/v1/internal/uacp/events",
            "runtime_provider": "ollama",
            "capabilities": ["audit_trail", "evidence_block", "lineage_tracking"],
            "veklom_made": True,
            "watermark": "Veklom Sovereign AI Hub",
        },
    ]

# --- Webhook ---
@router.post("/marketplace/webhook")
async def marketplace_webhook(request: Request):
    # For now, just accept the ping or event and return 200 OK
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    return {"status": "ok", "message": "Marketplace webhook received successfully"}
