"""Provider management API — BYOK CRUD, routing status, and audit logs.

Endpoints:
  GET    /providers/available          — list providers available to this tenant
  GET    /providers/keys               — list tenant's BYOK keys (no raw values)
  POST   /providers/keys               — add a BYOK key (encrypted at rest)
  PATCH  /providers/keys/{key_id}      — update label / enable / disable
  DELETE /providers/keys/{key_id}      — remove a BYOK key
  GET    /providers/routing/logs       — routing audit log for this workspace
  GET    /providers/routing/status     — live provider health / availability
  POST   /providers/routing/test       — test a provider key (returns ok/fail, no key in response)
  GET    /providers/routing/rules      — show current routing policy for this tenant
"""

import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.ai.provider_router import (
    _configured_provider,
    is_founder_tenant,
    provider_order_for_tenant,
)
from backend.core.config.settings import settings
from backend.core.database.database import get_db
from backend.core.security.auth import get_current_user
from backend.core.security.key_encryption import decrypt_key, encrypt_key, key_prefix
from backend.db.models.provider import ProviderKey, ProviderRoutingLog

router = APIRouter(prefix="/providers", tags=["Providers"])

SUPPORTED_PROVIDERS = ["ollama", "groq", "openai", "gemini", "huggingface", "anthropic"]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Available providers for this tenant
# ---------------------------------------------------------------------------

@router.get("/available")
async def list_available_providers(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return providers available to this tenant with status and key source."""
    workspace_id = user.workspace_id or ""
    founder = is_founder_tenant(workspace_id)

    # Load BYOK keys for this workspace
    result = await db.execute(
        select(ProviderKey).where(
            ProviderKey.workspace_id == workspace_id,
            ProviderKey.is_active == True,
        )
    )
    byok = {k.provider: k for k in result.scalars().all()}

    providers = []
    for p in SUPPORTED_PROVIDERS:
        available = False
        key_source = None
        label = None

        if p == "ollama":
            available = _configured_provider("ollama")
            key_source = "default"
            label = "Default — always available"
        elif founder and _configured_provider(p):
            available = True
            key_source = "owner"
            label = "Owner-configured"
        elif p in byok:
            available = True
            key_source = "byok"
            label = byok[p].label or "Tenant BYOK"

        providers.append({
            "provider": p,
            "available": available,
            "key_source": key_source,
            "label": label,
            "is_default": p == "ollama",
            "requires_byok": p != "ollama" and not founder,
        })

    order, reason = provider_order_for_tenant({}, workspace_id)

    return {
        "workspace_id": workspace_id,
        "is_founder_tenant": founder,
        "default_provider": "ollama",
        "routing_order": order,
        "providers": providers,
        "routing_policy": {
            "description": "Ollama first. Escalate only when needed and authorized.",
            "ollama_primary": True,
            "customer_byok_enabled": True,
            "founder_full_access": founder,
        },
    }


# ---------------------------------------------------------------------------
# BYOK key management (keys are always encrypted at rest, never in responses)
# ---------------------------------------------------------------------------

@router.get("/keys")
async def list_provider_keys(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List BYOK keys for this workspace — raw values are NEVER returned."""
    workspace_id = user.workspace_id or ""
    result = await db.execute(
        select(ProviderKey).where(ProviderKey.workspace_id == workspace_id)
    )
    keys = result.scalars().all()
    return [
        {
            "id": k.id,
            "provider": k.provider,
            "label": k.label,
            "key_prefix": k.key_prefix,
            "is_active": k.is_active,
            "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
            "created_at": k.created_at.isoformat() if k.created_at else None,
            "extra_config": k.extra_config or {},
        }
        for k in keys
    ]


@router.post("/keys")
async def add_provider_key(
    body: dict,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a BYOK provider key. Raw key is encrypted immediately, never stored in plaintext."""
    workspace_id = user.workspace_id or ""
    provider = (body.get("provider") or "").strip().lower()
    raw_key = (body.get("key") or "").strip()
    label = (body.get("label") or "").strip()

    if provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")
    if not raw_key:
        raise HTTPException(status_code=400, detail="key is required")
    if len(raw_key) < 8:
        raise HTTPException(status_code=400, detail="key too short")

    # Founder keys are managed via env vars only — customers cannot set founder keys
    if is_founder_tenant(workspace_id) and body.get("is_founder_key"):
        raise HTTPException(status_code=403, detail="Use environment variables for owner-level provider keys")

    encrypted = encrypt_key(raw_key)
    prefix = key_prefix(raw_key)

    key_row = ProviderKey(
        workspace_id=workspace_id,
        user_id=user.id,
        provider=provider,
        label=label or f"{provider.capitalize()} BYOK",
        key_encrypted=encrypted,
        key_prefix=prefix,
        extra_config=body.get("extra_config") or {},
        is_founder_key=False,
    )
    db.add(key_row)
    await db.commit()
    await db.refresh(key_row)

    return {
        "id": key_row.id,
        "provider": key_row.provider,
        "label": key_row.label,
        "key_prefix": key_row.key_prefix,
        "is_active": key_row.is_active,
        "created_at": key_row.created_at.isoformat() if key_row.created_at else None,
    }


@router.patch("/keys/{key_id}")
async def update_provider_key(
    key_id: str,
    body: dict,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    workspace_id = user.workspace_id or ""
    result = await db.execute(
        select(ProviderKey).where(
            ProviderKey.id == key_id,
            ProviderKey.workspace_id == workspace_id,
        )
    )
    key_row = result.scalar_one_or_none()
    if not key_row:
        raise HTTPException(status_code=404, detail="Provider key not found")

    if "label" in body:
        key_row.label = body["label"]
    if "is_active" in body:
        key_row.is_active = bool(body["is_active"])
    if "extra_config" in body:
        key_row.extra_config = body["extra_config"]

    await db.commit()
    return {"id": key_row.id, "provider": key_row.provider, "label": key_row.label, "is_active": key_row.is_active}


@router.delete("/keys/{key_id}")
async def delete_provider_key(
    key_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    workspace_id = user.workspace_id or ""
    result = await db.execute(
        select(ProviderKey).where(
            ProviderKey.id == key_id,
            ProviderKey.workspace_id == workspace_id,
        )
    )
    key_row = result.scalar_one_or_none()
    if not key_row:
        raise HTTPException(status_code=404, detail="Provider key not found")
    await db.delete(key_row)
    await db.commit()
    return {"deleted": True, "id": key_id}


# ---------------------------------------------------------------------------
# Routing audit logs
# ---------------------------------------------------------------------------

@router.get("/routing/logs")
async def get_routing_logs(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = 50,
    offset: int = 0,
):
    """Return routing audit log — shows why Ollama was used or why escalation happened."""
    workspace_id = user.workspace_id or ""
    result = await db.execute(
        select(ProviderRoutingLog)
        .where(ProviderRoutingLog.workspace_id == workspace_id)
        .order_by(ProviderRoutingLog.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    logs = result.scalars().all()
    return [
        {
            "id": log.id,
            "provider_selected": log.provider_selected,
            "model_selected": log.model_selected,
            "escalated": log.escalated,
            "escalation_reason": log.escalation_reason,
            "provider_chain_tried": log.provider_chain_tried,
            "key_source": log.key_source,
            "latency_ms": log.latency_ms,
            "success": log.success,
            "error_detail": log.error_detail if not log.success else None,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]


# ---------------------------------------------------------------------------
# Routing status and rules
# ---------------------------------------------------------------------------

@router.get("/routing/status")
async def routing_status(user=Depends(get_current_user)):
    """Live provider availability for this tenant."""
    workspace_id = user.workspace_id or ""
    founder = is_founder_tenant(workspace_id)

    statuses = {}
    for p in SUPPORTED_PROVIDERS:
        if p == "ollama":
            configured = _configured_provider("ollama")
            statuses[p] = {"available": configured, "source": "default", "base_url": settings.OLLAMA_BASE_URL}
        elif founder:
            configured = _configured_provider(p)
            statuses[p] = {"available": configured, "source": "owner_key" if configured else "not_configured"}
        else:
            statuses[p] = {"available": False, "source": "byok_required"}

    order, _ = provider_order_for_tenant({}, workspace_id)
    return {
        "workspace_id": workspace_id,
        "is_founder_tenant": founder,
        "active_primary": "ollama",
        "routing_order": order,
        "providers": statuses,
        "timestamp": _utcnow().isoformat(),
    }


@router.get("/routing/rules")
async def routing_rules(user=Depends(get_current_user)):
    """Show the routing policy applied to this tenant."""
    workspace_id = user.workspace_id or ""
    founder = is_founder_tenant(workspace_id)
    order, _ = provider_order_for_tenant({}, workspace_id)

    return {
        "workspace_id": workspace_id,
        "is_founder_tenant": founder,
        "policy": {
            "default_provider": "ollama",
            "ollama_first": True,
            "escalation_enabled": founder,
            "escalation_triggers": [
                "tool_support_required",
                "long_context",
                "specific_model_requested",
                "low_latency_streaming",
            ],
            "customer_access": {
                "ollama": "always",
                "other_providers": "byok_only",
                "owner_keys": "never",
            },
            "founder_access": {
                "ollama": "always",
                "groq": "if_configured",
                "huggingface": "if_configured",
                "gemini": "if_configured",
                "openai": "if_configured",
            },
            "key_security": {
                "encrypted_at_rest": True,
                "algorithm": "Fernet-AES128-CBC-HMAC-SHA256",
                "keys_in_logs": False,
                "keys_in_api_responses": False,
                "audit_every_selection": True,
            },
        },
        "routing_order": order,
    }


@router.post("/routing/test")
async def test_provider_key(
    body: dict,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Test a BYOK key by ID — returns ok/fail without exposing the key value."""
    key_id = body.get("key_id")
    if not key_id:
        raise HTTPException(status_code=400, detail="key_id required")

    workspace_id = user.workspace_id or ""
    result = await db.execute(
        select(ProviderKey).where(
            ProviderKey.id == key_id,
            ProviderKey.workspace_id == workspace_id,
        )
    )
    key_row = result.scalar_one_or_none()
    if not key_row:
        raise HTTPException(status_code=404, detail="Provider key not found")

    try:
        raw_key = decrypt_key(key_row.key_encrypted)
    except ValueError:
        return {"ok": False, "provider": key_row.provider, "error": "Key decryption failed"}

    import httpx as _httpx
    provider = key_row.provider
    start = time.time()
    try:
        if provider in {"openai", "groq", "huggingface"}:
            from backend.core.ai.provider_router import _openai_compatible_config
            url, _ = _openai_compatible_config(provider)
            async with _httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.post(
                    url,
                    headers={"Authorization": f"Bearer {raw_key}", "Content-Type": "application/json"},
                    json={"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "ping"}], "max_tokens": 1},
                )
            ok = resp.status_code < 400
            detail = None if ok else f"HTTP {resp.status_code}"
        elif provider == "gemini":
            async with _httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
                    params={"key": raw_key},
                    json={"contents": [{"parts": [{"text": "ping"}]}]},
                )
            ok = resp.status_code < 400
            detail = None if ok else f"HTTP {resp.status_code}"
        else:
            return {"ok": None, "provider": provider, "error": "Test not supported for this provider"}

        latency_ms = int((time.time() - start) * 1000)
        if ok:
            key_row.last_used_at = _utcnow()
            await db.commit()

        return {"ok": ok, "provider": provider, "latency_ms": latency_ms, "error": detail}
    except Exception as exc:
        return {"ok": False, "provider": provider, "error": str(exc)[:200]}
