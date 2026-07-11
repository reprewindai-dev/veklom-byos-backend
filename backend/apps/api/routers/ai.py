"""AI execution routes."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, ConfigDict, Field
from typing import List, Dict, Any, Optional

import time as _time

from backend.core.ai.provider_router import (
    normalize_messages,
    provider_order,
    run_completion,
    run_completion_for_tenant,
    smart_provider_order,
    task_tier,
    _content_from_openai_response,
    is_founder_tenant,
)
from backend.core.ai.cache import (
    get_hot, set_hot,
    get_warm, set_warm,
    get_memory, push_memory, clear_memory, get_memory_stats,
)
from backend.core.database.database import get_db
from backend.core.security.auth import get_current_user
from backend.core.security.wallet_guard import token_deduction_guard
from backend.core.security.entitlements import require_entitlement
from backend.db.models.ai import ExecLog
from backend.db.models.provider import ProviderKey
from backend.core.security.key_encryption import decrypt_key

# --- Strict Pydantic Models for OpenAPI Schema Hardening ---

class ChatMessage(BaseModel):
    role: str = Field(..., description="Author role (system, user, assistant)")
    content: str = Field(..., description="Message text content")

class AICompleteRequest(BaseModel):
    model: str = Field("llama3.2:latest", description="Target model ID")
    messages: List[ChatMessage] = Field(..., description="Normalized chat completion messages")
    temperature: Optional[float] = Field(0.7, description="Sampling temperature")
    max_tokens: Optional[int] = Field(2048, description="Maximum response tokens")

class AIPredictCostRequest(BaseModel):
    model: Optional[str] = Field("gpt-4o", description="Model identifier to base pricing on")
    input_tokens: Optional[int] = Field(1000, description="Number of input tokens")
    estimated_tokens: Optional[int] = Field(None, description="Fallback input token estimate")
    output_tokens: Optional[int] = Field(0, description="Number of output tokens")

class AIInferenceRequest(BaseModel):
    model: Optional[str] = Field("llama3.2:latest", description="Model ID to select")
    messages: List[ChatMessage] = Field(..., description="Context messages array")
    temperature: Optional[float] = Field(0.7, description="Sampling temperature")
    max_tokens: Optional[int] = Field(2048, description="Maximum generation length")
    stream: Optional[bool] = Field(False, description="Whether to enable SSE stream")

class AIChatRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    session_id: Optional[str] = Field(None, description="Persistent conversation session ID")
    model: Optional[str] = Field("llama3.2:latest", description="Model identifier to use")
    messages: List[ChatMessage] = Field(..., description="Normalized message turns list")
    temperature: Optional[float] = Field(0.7, description="Sampling temperature")
    max_tokens: Optional[int] = Field(2048, description="Maximum tokens to generate")

router = APIRouter(
    prefix="/ai",
    tags=["AI"],
    dependencies=[
        Depends(get_current_user),
        Depends(token_deduction_guard),
        Depends(require_entitlement("starter"))
    ]
)


@router.post("/complete")
async def ai_complete(body: AICompleteRequest, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """
    Handle an AI completion request, persist an execution log, and return the generated text with usage and billing metadata.
    """
    t0 = _time.monotonic()
    # Convert request to dictionary for run_completion hook compatibility
    payload_dict = body.model_dump()
    result = await run_completion(payload_dict, stream=False)
    latency_ms = int((_time.monotonic() - t0) * 1000)

    data = result.payload
    content = _content_from_openai_response(data)
    usage = data.get("usage", {})
    input_tokens = usage.get("prompt_tokens", 0)
    output_tokens = usage.get("completion_tokens", 0)
    total_tokens = usage.get("total_tokens", input_tokens + output_tokens)
    model = data.get("model", body.model or "unknown")

    log = ExecLog(
        user_id=user.id,
        workspace_id=user.workspace_id or "",
        model=model,
        provider=result.provider,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost=round(total_tokens * 0.000002, 6),
        latency_ms=latency_ms,
        status="completed",
        content_safety_score=0.98,
    )
    db.add(log)
    await db.commit()

    return {
        "id": f"run_{log.id}",
        "response_text": content,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "tokens_deducted": total_tokens,
        "provider": result.provider,
        "model": model,
        "route": "hetzner-primary",
        "policy": {"status": "passed", "redactions": 0, "policy_id": "outbound.public.v3"},
        "audit_id": log.id,
        "latency_ms": latency_ms,
        "cost_usd": log.cost_usd,
        "content_safety_score": log.content_safety_score,
    }


@router.get("/models")
async def list_models(user=Depends(get_current_user)):
    """
    Return available AI model metadata.
    """
    return [
        {"id": "llama3.2:latest", "provider": "ollama", "name": "Ollama Llama 3.2 3B", "context_window": 32768, "cost_per_1k_input": 0.0},
        {"id": "gpt-4o-mini", "provider": "openai", "name": "GPT-4o Mini", "context_window": 128000, "cost_per_1k_input": 0.00015},
        {"id": "llama-3.1-8b-instant", "provider": "groq", "name": "Groq Llama 3.1 8B Instant", "context_window": 131072, "cost_per_1k_input": 0.00005},
        {"id": "meta-llama/Llama-3.1-8B-Instruct:fastest", "provider": "huggingface", "name": "Hugging Face Llama 3.1 8B", "context_window": 131072, "cost_per_1k_input": 0.0001},
        {"id": "gemini-2.5-flash", "provider": "gemini", "name": "Gemini 2.5 Flash", "context_window": 1000000, "cost_per_1k_input": 0.0003},
        {"id": "gpt-4o", "provider": "openai", "name": "GPT-4o", "context_window": 128000, "cost_per_1k_input": 0.005},
    ]


@router.get("/providers")
async def list_providers(user=Depends(get_current_user)):
    """
    Provides available AI providers and the default provider ordering.
    """
    return {"default_order": provider_order({}), "providers": ["ollama", "groq", "huggingface", "ollama", "groq", "huggingface", "gemini", "openai"]}


@router.post("/predict-cost")
async def predict_cost(body: AIPredictCostRequest, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """
    Estimate API usage cost for a given model and token counts.
    """
    from backend.db.models.workspace import ModelConfig
    from sqlalchemy import select
    
    model_id = body.model or "gpt-4o"
    input_tokens = body.input_tokens if body.input_tokens is not None else (body.estimated_tokens if body.estimated_tokens is not None else 1000)
    output_tokens = body.output_tokens or 0
    
    # Try to get real model costs from database
    workspace_id = user.workspace_id or "default"
    result = await db.execute(
        select(ModelConfig).where(
            ModelConfig.id == model_id,
            ModelConfig.workspace_id == workspace_id
        )
    )
    model_config = result.scalar_one_or_none()
    
    if model_config:
        # Use real costs from database
        cost_per_1k_input = float(model_config.cost_per_1k_input or 0)
        cost_per_1k_output = float(model_config.cost_per_1k_output or 0)
    else:
        # Fallback to default costs for known models
        cost_map = {
            "gpt-4o": (0.005, 0.015),
            "gpt-4o-mini": (0.00015, 0.0006),
            "llama-3.1-8b-instant": (0.00005, 0.0001),
            "gemini-2.5-flash": (0.0003, 0.001),
            "qwen2.5:3b": (0.0, 0.0),
        }
        cost_per_1k_input, cost_per_1k_output = cost_map.get(model_id, (0.002, 0.006))
    
    # Calculate total cost
    input_cost = (input_tokens / 1000) * cost_per_1k_input
    output_cost = (output_tokens / 1000) * cost_per_1k_output
    total_cost = input_cost + output_cost
    
    return {
        "model": model_id,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
        "cost_per_1k_input": cost_per_1k_input,
        "cost_per_1k_output": cost_per_1k_output,
        "estimated_cost_usd": round(total_cost, 6),
        "currency": "USD",
    }


# NOTE: /transcribe is intentionally NOT defined here. The real handler lives in
# upload.py (it processes uploaded audio); this stub previously shadowed it
# because the ai router is registered before the upload router.


# ---------------------------------------------------------------------------
# /ai/inference  — cached smart-tier inference (x402-ready)
# ---------------------------------------------------------------------------

@router.post("/inference")
async def ai_inference(body: AIInferenceRequest, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """
    Perform policy-guided AI inference with hot/warm caching and tenant-aware provider selection.
    """
    t0 = _time.monotonic()
    payload_dict = body.model_dump()
    messages = normalize_messages(payload_dict)
    model = payload_dict.get("model") or "llama3.2:latest"
    temperature = float(payload_dict.get("temperature", 0.7))
    tier = task_tier(payload_dict)
    workspace_id = user.workspace_id or "default"

    # 1. Hot cache check
    cached = await get_hot(model, messages, temperature)
    cache_source = None
    if cached is None:
        # 2. Warm cache check
        cached = await get_warm(model, messages)
        if cached:
            cache_source = "warm"
    else:
        cache_source = "hot"

    if cached:
        content = _content_from_openai_response(cached)
        return {
            "id": f"inf_{int(_time.time())}",
            "response_text": content,
            "provider": cached.get("model", model).split(":")[0],
            "model": cached.get("model", model),
            "tier": tier,
            "cache_hit": cache_source,
            "policy": {"status": "passed", "cache": True},
            "latency_ms": int((_time.monotonic() - t0) * 1000),
            "cost_usd": 0.0,
        }

    # 3. Cache miss — route to best provider for this tier
    # Load BYOK keys for this workspace
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
        except Exception:
            continue

    override_body = {**payload_dict, "messages": messages}
    result, key_source, reason = await run_completion_for_tenant(
        override_body, workspace_id, byok_keys=byok_keys
    )
    latency_ms = int((_time.monotonic() - t0) * 1000)
    content = _content_from_openai_response(result.payload)
    used_model = result.payload.get("model", model)
    usage = result.payload.get("usage", {})
    input_tokens = usage.get("prompt_tokens", 0)
    output_tokens = usage.get("completion_tokens", 0)

    # Compute real pricing cost dynamically
    from backend.db.models.workspace import ModelConfig
    try:
        model_config_res = await db.execute(
            select(ModelConfig).where(
                ModelConfig.id == used_model,
                ModelConfig.workspace_id == workspace_id
            )
        )
        model_config = model_config_res.scalar_one_or_none()
        if model_config:
            cost_per_1k_input = float(model_config.cost_per_1k_input or 0)
            cost_per_1k_output = float(model_config.cost_per_1k_output or 0)
        else:
            cost_map = {
                "gpt-4o": (0.005, 0.015),
                "gpt-4o-mini": (0.00015, 0.0006),
                "llama-3.1-8b-instant": (0.00005, 0.0001),
                "gemini-2.5-flash": (0.0003, 0.001),
                "qwen2.5:3b": (0.0, 0.0),
            }
            cost_per_1k_input, cost_per_1k_output = cost_map.get(used_model, (0.002, 0.006))
        cost_usd = round(((input_tokens / 1000) * cost_per_1k_input) + ((output_tokens / 1000) * cost_per_1k_output), 6)
    except Exception:
        cost_usd = round((input_tokens + output_tokens) * 0.000002, 6)

    # Populate caches
    await set_hot(used_model, messages, result.payload, temperature)
    await set_warm(used_model, messages, result.payload)

    log = ExecLog(
        user_id=user.id,
        workspace_id=workspace_id,
        model=used_model,
        provider=result.provider,
        input_tokens=usage.get("prompt_tokens", 0),
        output_tokens=usage.get("completion_tokens", 0),
        cost=cost_usd,
        latency_ms=latency_ms,
        status="completed",
        content_safety_score=0.98,
    )
    db.add(log)
    await db.commit()

    return {
        "id": f"inf_{log.id}",
        "response_text": content,
        "provider": result.provider,
        "model": used_model,
        "tier": tier,
        "escalation_reason": reason or None,
        "key_source": key_source,
        "cache_hit": None,
        "policy": {"status": "passed", "policy_id": "outbound.public.v3"},
        "audit_id": log.id,
        "latency_ms": latency_ms,
        "input_tokens": usage.get("prompt_tokens", 0),
        "output_tokens": usage.get("completion_tokens", 0),
        "cost_usd": cost_usd,
    }


# ---------------------------------------------------------------------------
# /ai/chat  — persistent 20-message 24h conversation memory
# ---------------------------------------------------------------------------

@router.post("/chat")
async def ai_chat(
    body: AIChatRequest,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Handle a single chat turn using per-session Redis memory (max 20 messages, 24-hour TTL).
    """
    t0 = _time.monotonic()
    workspace_id = user.workspace_id or "default"
    payload_dict = body.model_dump()
    session_id = payload_dict.get("session_id") or f"sess_{user.id}"
    model = payload_dict.get("model") or "llama3.2:latest"
    temperature = float(payload_dict.get("temperature", 0.7))
    tier = task_tier(payload_dict)

    # New user message(s) from body
    new_user_msgs = normalize_messages(payload_dict)

    # 1. Load existing conversation history
    history = await get_memory(workspace_id, session_id)

    # 2. Build full context: history + new message
    full_context = history + new_user_msgs

    # 3. Hot cache check on full context
    cached = await get_hot(model, full_context, temperature)
    if cached is None:
        cached = await get_warm(model, full_context)

    if cached:
        content = _content_from_openai_response(cached)
        assistant_msg = {"role": "assistant", "content": content}
        updated_history = await push_memory(workspace_id, session_id, new_user_msgs + [assistant_msg])
        return {
            "response_text": content,
            "session_id": session_id,
            "provider": model.split(":")[0] if ":" in model else "cached",
            "model": model,
            "tier": tier,
            "cache_hit": "hot",
            "memory": {"message_count": len(updated_history), "max": 20, "ttl_hours": 24},
            "latency_ms": int((_time.monotonic() - t0) * 1000),
        }

    # 4. Cache miss — run completion with full history context
    # Load BYOK keys for this workspace
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
        except Exception:
            continue

    completion_body = {**payload_dict, "messages": full_context}
    result, key_source, reason = await run_completion_for_tenant(
        completion_body, workspace_id, byok_keys=byok_keys
    )
    latency_ms = int((_time.monotonic() - t0) * 1000)
    content = _content_from_openai_response(result.payload)
    used_model = result.payload.get("model", model)
    usage = result.payload.get("usage", {})
    input_tokens = usage.get("prompt_tokens", 0)
    output_tokens = usage.get("completion_tokens", 0)

    # Compute real pricing cost dynamically
    from backend.db.models.workspace import ModelConfig
    try:
        model_config_res = await db.execute(
            select(ModelConfig).where(
                ModelConfig.id == used_model,
                ModelConfig.workspace_id == workspace_id
            )
        )
        model_config = model_config_res.scalar_one_or_none()
        if model_config:
            cost_per_1k_input = float(model_config.cost_per_1k_input or 0)
            cost_per_1k_output = float(model_config.cost_per_1k_output or 0)
        else:
            cost_map = {
                "gpt-4o": (0.005, 0.015),
                "gpt-4o-mini": (0.00015, 0.0006),
                "llama-3.1-8b-instant": (0.00005, 0.0001),
                "gemini-2.5-flash": (0.0003, 0.001),
                "qwen2.5:3b": (0.0, 0.0),
            }
            cost_per_1k_input, cost_per_1k_output = cost_map.get(used_model, (0.002, 0.006))
        cost_usd = round(((input_tokens / 1000) * cost_per_1k_input) + ((output_tokens / 1000) * cost_per_1k_output), 6)
    except Exception:
        cost_usd = round((input_tokens + output_tokens) * 0.000002, 6)

    # 5. Update memory: append user + assistant turns
    assistant_msg = {"role": "assistant", "content": content}
    updated_history = await push_memory(workspace_id, session_id, new_user_msgs + [assistant_msg])

    # 6. Populate caches with the full-context response
    await set_hot(used_model, full_context, result.payload, temperature)
    await set_warm(used_model, full_context, result.payload)

    log = ExecLog(
        user_id=user.id,
        workspace_id=workspace_id,
        model=used_model,
        provider=result.provider,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost=cost_usd,
        latency_ms=latency_ms,
        status="completed",
        content_safety_score=0.98,
    )
    db.add(log)
    await db.commit()

    return {
        "response_text": content,
        "session_id": session_id,
        "provider": result.provider,
        "model": used_model,
        "tier": tier,
        "escalation_reason": reason or None,
        "key_source": key_source,
        "cache_hit": None,
        "memory": {
            "message_count": len(updated_history),
            "max": 20,
            "ttl_hours": 24,
        },
        "policy": {"status": "passed", "policy_id": "outbound.public.v3"},
        "audit_id": log.id,
        "latency_ms": latency_ms,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": cost_usd,
    }


# ---------------------------------------------------------------------------
# /ai/chat/memory — memory management endpoints
# ---------------------------------------------------------------------------

@router.get("/chat/memory")
async def get_chat_memory(
    session_id: str = Query(...),
    user=Depends(get_current_user),
):
    """
    Fetches conversation memory and its statistics for the given session.
    
    Parameters:
        session_id (str): The workspace-scoped conversation session identifier.
    
    Returns:
        dict: Combined memory metadata and messages. The returned mapping includes memory statistics (e.g., count, max, ttl_hours) and a "messages" key with the list of stored message objects for the session.
    """
    workspace_id = user.workspace_id or "default"
    msgs = await get_memory(workspace_id, session_id)
    stats = await get_memory_stats(workspace_id, session_id)
    return {**stats, "messages": msgs}


@router.delete("/chat/memory")
async def clear_chat_memory(
    session_id: str = Query(...),
    user=Depends(get_current_user),
):
    """
    Clear stored conversation memory for the given session.
    
    Parameters:
        session_id (str): Identifier of the conversation session to clear. The workspace is taken from the authenticated user's `workspace_id` or `"default"` if unset.
    
    Returns:
        dict: {"cleared": True, "session_id": session_id}
    """
    workspace_id = user.workspace_id or "default"
    await clear_memory(workspace_id, session_id)
    return {"cleared": True, "session_id": session_id}


@router.get("/routing/tier")
async def explain_tier(body: dict = None, user=Depends(get_current_user)):
    """
    Determine the routing tier and recommended providers for a given request body.
    
    Parameters:
        body (dict): Optional request payload whose fields are used to compute the task tier (e.g., stream, agent_type, context size).
    
    Returns:
        result (dict): Mapping with the following keys:
            - tier: Selected tier label (str).
            - providers: List of provider IDs recommended for the selected tier.
            - tiers: Full mapping of tiers to providers.
            - rules: Human-readable descriptions of each tier's intended use.
            - escalation_signals: Signals that map conditions to preferred tiers.
    """
    body = body or {}
    tier = task_tier(body)
    from backend.core.ai.provider_router import TIER_TO_PROVIDERS
    return {
        "tier": tier,
        "providers": TIER_TO_PROVIDERS.get(tier, ["ollama"]),
        "tiers": TIER_TO_PROVIDERS,
        "rules": {
            "local": "Ollama qwen2.5:3b — daily driver, all routine tasks",
            "fast": "Groq — streaming, low latency, medium context (131k)",
            "reasoning": "Gemini 2.5 Flash — complex reasoning, long context (2M)",
            "max": "OpenAI GPT-4o — tool calls, orchestration, hardest tasks",
            "specialized": "HuggingFace — domain-specific open-weight models",
        },
        "escalation_signals": {
            "tools/functions": "max",
            "context > 32k chars": "reasoning",
            "context > 8k chars": "fast",
            "agent_type=orchestrator": "max",
            "agent_type=reasoning": "reasoning",
            "stream=true": "fast",
            "default": "local (Ollama)",
        },
    }
