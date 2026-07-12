"""Service layer for governed AI provider routing (BYOK)."""

import json
import logging
import time
from typing import AsyncIterator, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.ai.provider_router import (
    CompletionResult,
    run_completion_for_tenant,
    provider_order_for_tenant,
    stream_completion_for_tenant,
    is_founder_tenant,
)
from backend.core.security.key_encryption import decrypt_key
from backend.db.models.provider import ProviderKey, ProviderRoutingLog

logger = logging.getLogger(__name__)


async def _get_byok_keys(db: AsyncSession, workspace_id: str) -> dict[str, str]:
    """Retrieve and decrypt active BYOK keys for a workspace."""
    keys_res = await db.execute(
        select(ProviderKey).where(
            ProviderKey.workspace_id == workspace_id,
            ProviderKey.is_active == True,
        )
    )
    byok_keys = {}
    for k in keys_res.scalars().all():
        try:
            byok_keys[k.provider] = decrypt_key(k.key_encrypted)
        except Exception as e:
            logger.error(f"Failed to decrypt BYOK key for {k.provider}: {e}")
            continue
    return byok_keys


async def _log_routing_decision(
    db: AsyncSession,
    workspace_id: str,
    user_id: str,
    exec_log_id: str,
    provider_selected: str,
    model_selected: str,
    escalated: bool,
    escalation_reason: str,
    provider_chain_tried: list[str],
    key_source: str,
    latency_ms: int,
    success: bool,
    error_detail: str = "",
    request_metadata: Optional[dict] = None,
):
    """Persist the routing audit log."""
    try:
        # Resolve key_id if it's byok
        key_id = ""
        if key_source == "byok":
            res = await db.execute(
                select(ProviderKey.id).where(
                    ProviderKey.workspace_id == workspace_id,
                    ProviderKey.provider == provider_selected,
                    ProviderKey.is_active == True
                ).limit(1)
            )
            key_id = res.scalar_one_or_none() or ""

        log_entry = ProviderRoutingLog(
            workspace_id=workspace_id,
            user_id=user_id,
            exec_log_id=exec_log_id or "",
            provider_selected=provider_selected,
            model_selected=model_selected,
            escalated=escalated,
            escalation_reason=escalation_reason,
            provider_chain_tried=provider_chain_tried,
            key_source=key_source,
            key_id=key_id,
            latency_ms=latency_ms,
            success=success,
            error_detail=error_detail,
            request_metadata=request_metadata or {}
        )
        db.add(log_entry)
        await db.commit()
    except Exception as e:
        logger.error(f"Failed to record ProviderRoutingLog: {e}")
        # Don't fail the inference if audit logging fails


async def execute_governed_inference(
    db: AsyncSession,
    workspace_id: str,
    user_id: str,
    body: dict,
    exec_log_id: str = ""
) -> Tuple[CompletionResult, str, str, int]:
    """Execute a synchronous completion and write the routing audit log."""
    t0 = time.monotonic()
    
    byok_keys = await _get_byok_keys(db, workspace_id)
    
    provider_chain_tried, escalation_reason = provider_order_for_tenant(body, workspace_id)
    escalated = len(provider_chain_tried) > 0 and provider_chain_tried[0] != "ollama"
    
    try:
        result, key_source, reason = await run_completion_for_tenant(
            body, workspace_id, byok_keys=byok_keys
        )
        latency_ms = int((time.monotonic() - t0) * 1000)
        
        # Log success
        await _log_routing_decision(
            db=db,
            workspace_id=workspace_id,
            user_id=user_id,
            exec_log_id=exec_log_id,
            provider_selected=result.provider,
            model_selected=result.payload.get("model", ""),
            escalated=escalated,
            escalation_reason=reason or escalation_reason,
            provider_chain_tried=provider_chain_tried,
            key_source=key_source,
            latency_ms=latency_ms,
            success=True,
            request_metadata={"body_keys": list(body.keys())}
        )
        
        return result, key_source, reason, latency_ms
        
    except Exception as e:
        latency_ms = int((time.monotonic() - t0) * 1000)
        # Log failure
        await _log_routing_decision(
            db=db,
            workspace_id=workspace_id,
            user_id=user_id,
            exec_log_id=exec_log_id,
            provider_selected="failed",
            model_selected=body.get("model", ""),
            escalated=escalated,
            escalation_reason=escalation_reason,
            provider_chain_tried=provider_chain_tried,
            key_source="unknown",
            latency_ms=latency_ms,
            success=False,
            error_detail=str(e),
            request_metadata={"body_keys": list(body.keys())}
        )
        raise


async def stream_governed_inference(
    db: AsyncSession,
    workspace_id: str,
    user_id: str,
    body: dict,
    exec_log_id: str = ""
) -> AsyncIterator[str]:
    """Execute a streaming completion and write the routing audit log."""
    t0 = time.monotonic()
    
    byok_keys = await _get_byok_keys(db, workspace_id)
    
    provider_chain_tried, escalation_reason = provider_order_for_tenant(body, workspace_id)
    escalated = len(provider_chain_tried) > 0 and provider_chain_tried[0] != "ollama"
    key_source = "owner" if is_founder_tenant(workspace_id) else "byok"
    
    stream_gen = stream_completion_for_tenant(body, workspace_id, byok_keys=byok_keys)
    
    provider_selected = "unknown"
    model_selected = body.get("model", "")
    success = False
    error_detail = ""
    
    try:
        async for chunk in stream_gen:
            if provider_selected == "unknown" and chunk.startswith("data: {"):
                try:
                    data = json.loads(chunk[6:])
                    if "id" in data:
                        provider_selected = data["id"].split("-")[0]
                        if provider_selected == "ollama":
                            key_source = "default"
                    if "model" in data:
                        model_selected = data["model"]
                except Exception:
                    pass
            
            if "error" in chunk:
                success = False
                error_detail = chunk
            elif "[DONE]" in chunk:
                success = True
                
            yield chunk
            
        latency_ms = int((time.monotonic() - t0) * 1000)
        
        await _log_routing_decision(
            db=db,
            workspace_id=workspace_id,
            user_id=user_id,
            exec_log_id=exec_log_id,
            provider_selected=provider_selected,
            model_selected=model_selected,
            escalated=escalated,
            escalation_reason=escalation_reason,
            provider_chain_tried=provider_chain_tried,
            key_source=key_source,
            latency_ms=latency_ms,
            success=success,
            error_detail=error_detail,
            request_metadata={"body_keys": list(body.keys()), "stream": True}
        )
        
    except Exception as e:
        latency_ms = int((time.monotonic() - t0) * 1000)
        await _log_routing_decision(
            db=db,
            workspace_id=workspace_id,
            user_id=user_id,
            exec_log_id=exec_log_id,
            provider_selected=provider_selected,
            model_selected=model_selected,
            escalated=escalated,
            escalation_reason=escalation_reason,
            provider_chain_tried=provider_chain_tried,
            key_source=key_source,
            latency_ms=latency_ms,
            success=False,
            error_detail=str(e),
            request_metadata={"body_keys": list(body.keys()), "stream": True}
        )
        raise
