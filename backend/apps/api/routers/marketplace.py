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
async def list_listings(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MarketplaceListing).where(MarketplaceListing.status == "published").limit(50))
    items = result.scalars().all()
    return [_listing_dict(i) for i in items]


@router.get("/listings/{listing_id}")
async def get_listing_short(listing_id: str, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MarketplaceListing).where(MarketplaceListing.id == listing_id))
    listing = result.scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    return _listing_dict(listing)


@router.get("/marketplace/listings/{listing_id}")
async def get_listing(listing_id: str, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MarketplaceListing).where(MarketplaceListing.id == listing_id))
    listing = result.scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    return _listing_dict(listing)


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


@router.patch("/listings/{listing_id}")
async def update_listing_short(listing_id: str, body: dict, user=Depends(get_current_user)):
    return {"id": listing_id, "updated": True, **body}


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


@router.post("/marketplace/listings/{listing_id}/install")
@router.post("/listings/{listing_id}/install")
async def install_listing(listing_id: str, body: dict = None, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Install a marketplace listing into the current workspace."""
    import uuid as _uuid
    from backend.db.models.marketplace import MarketplaceListing, InstalledAsset
    from sqlalchemy import select as _select
    from fastapi import HTTPException as _HTTPException

    body = body or {}
    target = body.get("target", user.workspace_id or "default")

    # Verify listing exists
    result = await db.execute(_select(MarketplaceListing).where(MarketplaceListing.id == listing_id))
    listing = result.scalar_one_or_none()
    if not listing:
        raise _HTTPException(status_code=404, detail="Listing not found")

    # Check if already installed
    existing = await db.execute(_select(InstalledAsset).where(
        InstalledAsset.workspace_id == target,
        InstalledAsset.listing_id == listing_id
    ))
    if existing.scalar_one_or_none():
        return {"id": listing_id, "status": "already_installed", "message": "This listing is already installed in your workspace"}

    # Create InstalledAsset record
    asset = InstalledAsset(
        id=str(_uuid.uuid4()),
        workspace_id=target,
        listing_id=listing_id,
        installed_by=user.id,
        asset_type=listing.category,
        name=listing.name,
        status="active",
        config_json=listing.config_json or {},
        version="1.0.0",
    )
    db.add(asset)

    # Increment listing downloads
    listing.downloads = (listing.downloads or 0) + 1

    await db.commit()
    await db.refresh(asset)

    return {
        "id": asset.id,
        "listing_id": listing_id,
        "workspace_id": target,
        "asset_type": asset.asset_type,
        "name": asset.name,
        "status": asset.status,
        "installed_at": asset.created_at.isoformat() if asset.created_at else None,
        "message": f"{listing.name} installed successfully",
    }


@router.get("/marketplace/installed")
@router.get("/installed")
async def list_installed(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """List all installed assets for the current workspace."""
    from backend.db.models.marketplace import InstalledAsset, MarketplaceListing
    from sqlalchemy import select as _select

    result = await db.execute(_select(InstalledAsset).where(InstalledAsset.workspace_id == (user.workspace_id or "default")))
    assets = result.scalars().all()

    return {
        "installed": [
            {
                "id": a.id,
                "listing_id": a.listing_id,
                "asset_type": a.asset_type,
                "name": a.name,
                "status": a.status,
                "version": a.version,
                "installed_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in assets
        ]
    }


@router.get("/marketplace/listings/{listing_id}/datasheet")
@router.get("/listings/{listing_id}/datasheet")
async def listing_datasheet(listing_id: str, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MarketplaceListing).where(MarketplaceListing.id == listing_id))
    listing = result.scalar_one_or_none()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    
    return {
        "listing_id": listing_id,
        "title": listing.name,
        "provider": listing.vendor_id,
        "category": listing.category,
        "positioning": listing.description,
        "price": listing.price,
        "compliance": listing.compliance_tags or [],
        "badges": listing.badges or [],
        "install_type": "managed",
        "target_infra": ["hetzner"],
        "datasheet_url": f"/api/v1/listings/{listing_id}/datasheet.pdf",
    }


# --- Marketplace Categories ---
@router.get("/marketplace/categories")
async def list_categories(user=Depends(get_current_user)):
    """Static category taxonomy used by the marketplace UI.

    Categories are not stored in the DB (every listing carries its own
    category string) so the canonical list lives here.  When a listing
    persists with a new category not in this taxonomy it is still surfaced
    by /listings; this endpoint just gives the UI the navigation tree.
    """
    return [
        {
            "slug": "governance",
            "name": "Governance / DevSecOps",
            "description": "Policy gates, repo review, audit, kill switches.",
            "products": ["repo-risk-gate"],
        },
        {
            "slug": "runtime",
            "name": "Runtime Modules",
            "description": "Compute routers, gradient field, IronGrid runtime.",
            "products": ["py03-irongrid"],
        },
        {
            "slug": "products",
            "name": "Products",
            "description": "First-party Veklom products and demos.",
            "products": ["lockerphycer"],
        },
        {
            "slug": "compliance",
            "name": "Compliance Packs",
            "description": "HIPAA, SOC2, PCI-DSS, GDPR pre-built bundles.",
            "products": [],
        },
        {
            "slug": "connectors",
            "name": "Connectors",
            "description": "Identity, SSO, observability, billing integrations.",
            "products": [],
        },
    ]


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
async def my_listings(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(MarketplaceListing).where(MarketplaceListing.vendor_id == user.id))
    listings = result.scalars().all()
    return [_listing_dict(l) for l in listings]


@router.get("/vendors/{vendor_id}")
async def get_vendor(vendor_id: str, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Vendor).where(Vendor.id == vendor_id))
    v = result.scalar_one_or_none()
    if v:
        return {"id": v.id, "business_name": v.business_name, "status": v.status}
    return {"id": vendor_id, "business_name": "Unknown Vendor", "status": "not_found"}


@router.get("/orders/{order_id}")
async def get_order(order_id: str, user=Depends(get_current_user)):
    return {"id": order_id, "status": "pending", "items": [], "total_usd": 0}


# --- Plugins ---
_PLUGIN_REGISTRY = {
    "p1": {"id": "p1", "name": "Document Parser", "category": "tool", "status": "active", "version": "1.2.0", "description": "Parses PDF, DOCX, HTML and emits structured chunks with metadata.", "author": "Veklom Native", "docs_url": "/docs/plugins/document-parser"},
    "p2": {"id": "p2", "name": "Code Analyzer", "category": "tool", "status": "active", "version": "2.0.1", "description": "Static analysis and security scanning for Python, TypeScript, and Go codebases.", "author": "Veklom Native", "docs_url": "/docs/plugins/code-analyzer"},
    "p3": {"id": "p3", "name": "Data Validator", "category": "governance", "status": "active", "version": "1.0.0", "description": "Schema and policy validation for structured data before LLM ingestion.", "author": "Veklom Native", "docs_url": "/docs/plugins/data-validator"},
    "p4": {"id": "p4", "name": "PII Redactor", "category": "privacy", "status": "active", "version": "3.1.0", "description": "Real-time PII detection and redaction proxy using NER + regex + LLM-assist.", "author": "Veklom Native", "docs_url": "/docs/plugins/pii-redactor"},
    "p5": {"id": "p5", "name": "Audit Sealer", "category": "evidence", "status": "active", "version": "1.4.0", "description": "Seals every action into a deterministic evidence block for SOC2 replay.", "author": "Veklom Native", "docs_url": "/docs/plugins/audit-sealer"},
}

_plugin_states: dict = {}


@router.get("/plugins")
async def list_plugins(user=Depends(get_current_user)):
    ws_id = getattr(user, "workspace_id", "") or ""
    result = []
    for pid, meta in _PLUGIN_REGISTRY.items():
        state = _plugin_states.get(f"{ws_id}:{pid}", True)
        result.append({**meta, "enabled": state, "status": "active" if state else "inactive"})
    return result


@router.post("/plugins/{plugin_id}/enable")
async def enable_plugin_mp(plugin_id: str, user=Depends(get_current_user)):
    ws_id = getattr(user, "workspace_id", "") or ""
    _plugin_states[f"{ws_id}:{plugin_id}"] = True
    meta = _PLUGIN_REGISTRY.get(plugin_id, {"id": plugin_id, "name": plugin_id})
    return {"id": plugin_id, "enabled": True, "status": "active", "name": meta.get("name", plugin_id)}


@router.post("/plugins/{plugin_id}/disable")
async def disable_plugin_mp(plugin_id: str, user=Depends(get_current_user)):
    ws_id = getattr(user, "workspace_id", "") or ""
    _plugin_states[f"{ws_id}:{plugin_id}"] = False
    meta = _PLUGIN_REGISTRY.get(plugin_id, {"id": plugin_id, "name": plugin_id})
    return {"id": plugin_id, "enabled": False, "status": "inactive", "name": meta.get("name", plugin_id)}


@router.get("/plugins/{plugin_id}/docs")
async def plugin_docs(plugin_id: str, user=Depends(get_current_user)):
    meta = _PLUGIN_REGISTRY.get(plugin_id)
    if not meta:
        return {"id": plugin_id, "docs": "No documentation available for this plugin.", "sections": []}
    return {
        "id": plugin_id,
        "name": meta["name"],
        "version": meta["version"],
        "description": meta["description"],
        "author": meta["author"],
        "docs": f"# {meta['name']}\n\n{meta['description']}\n\n## Installation\n\nEnabled per-workspace. No additional setup required.\n\n## Configuration\n\nNo configuration needed for the default setup.",
        "sections": [
            {"title": "Overview", "content": meta["description"]},
            {"title": "Usage", "content": f"This plugin is automatically activated for all pipelines in your workspace once enabled."},
            {"title": "Version history", "content": f"v{meta['version']} — current stable release."},
        ],
    }


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
