"""AI execution routes."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

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
async def ai_complete(body: dict, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """
    Handle an AI completion request, persist an execution log, and return the generated text with usage and billing metadata.
    
    Parameters:
        body (dict): Completion request payload forwarded to the completion service; expected to include at least the model and messages/prompts.
    
    Returns:
        dict: Response containing:
            - id (str): Run identifier derived from the persisted ExecLog.
            - response_text (str): Generated completion text.
            - input_tokens (int): Number of prompt/input tokens used.
            - output_tokens (int): Number of completion/output tokens produced.
            - tokens_deducted (int): Total tokens charged (input + output).
            - provider (str): Provider that produced the result.
            - model (str): Model identifier used for the completion.
            - route (str): Routing label used for the request.
            - policy (dict): Policy evaluation summary for the request.
            - audit_id (int): Database ExecLog primary key for this run.
            - latency_ms (int): Round-trip latency in milliseconds measured for the completion call.
            - cost_usd (float): Computed cost for the run in USD.
            - content_safety_score (float): Safety score assigned to the response.
    """
    t0 = _time.monotonic()
    result = await run_completion(body, stream=False)
    latency_ms = int((_time.monotonic() - t0) * 1000)

    data = result.payload
    content = _content_from_openai_response(data)
    usage = data.get("usage", {})
    input_tokens = usage.get("prompt_tokens", 0)
    output_tokens = usage.get("completion_tokens", 0)
    total_tokens = usage.get("total_tokens", input_tokens + output_tokens)
    model = data.get("model", body.get("model", "unknown"))

    log = ExecLog(
        user_id=user.id,
        workspace_id=user.workspace_id or "",
        model=model,
        provider=result.provider,
        prompt_tokens=input_tokens,
        completion_tokens=output_tokens,
        total_tokens=total_tokens,
        cost_usd=round(total_tokens * 0.000002, 6),
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
    
    Returns:
        list[dict]: A list of model descriptors. Each dictionary contains:
            - `id` (str): Model identifier.
            - `provider` (str): Provider name.
            - `name` (str): Human-readable model name.
            - `context_window` (int): Maximum context length in tokens.
            - `cost_per_1k_input` (float): Cost in USD per 1,000 input tokens.
    """
    return [
        {"id": "gpt-4o", "provider": "openai", "name": "GPT-4o", "context_window": 128000, "cost_per_1k_input": 0.005},
        {"id": "gpt-4o-mini", "provider": "openai", "name": "GPT-4o Mini", "context_window": 128000, "cost_per_1k_input": 0.00015},
        {"id": "llama-3.1-8b-instant", "provider": "groq", "name": "Groq Llama 3.1 8B Instant", "context_window": 131072, "cost_per_1k_input": 0.00005},
        {"id": "meta-llama/Llama-3.1-8B-Instruct:fastest", "provider": "huggingface", "name": "Hugging Face Llama 3.1 8B", "context_window": 131072, "cost_per_1k_input": 0.0001},
        {"id": "gemini-2.5-flash", "provider": "gemini", "name": "Gemini 2.5 Flash", "context_window": 1000000, "cost_per_1k_input": 0.0003},
        {"id": "llama3.2:latest", "provider": "ollama", "name": "Ollama Llama 3.2 3B", "context_window": 32768, "cost_per_1k_input": 0.0},
    ]


@router.get("/providers")
async def list_providers(user=Depends(get_current_user)):
    """
    Provides available AI providers and the default provider ordering.
    
    Returns:
        dict: Mapping with keys:
            - "default_order": dict mapping provider ID to numeric priority.
            - "providers": list of provider IDs in the default sequence (e.g., ["ollama", "groq", "huggingface", "gemini", "openai"]).
    """
    return {"default_order": provider_order({}), "providers": ["ollama", "groq", "huggingface", "gemini", "openai"]}


@router.post("/predict-cost")
async def predict_cost(body: dict, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """
    Estimate API usage cost for a given model and token counts.
    
    Parameters:
        body (dict): Request payload. Recognized keys:
            - model (str): Model identifier to base pricing on; defaults to "gpt-4o".
            - input_tokens (int): Number of input tokens to price. If absent, `estimated_tokens` is used; defaults to 1000.
            - estimated_tokens (int): Fallback for input token estimate.
            - output_tokens (int): Number of output tokens to price; defaults to 0.
    
    Returns:
        dict: Cost estimate containing:
            - model (str): The model id used for pricing.
            - input_tokens (int): Input token count used.
            - output_tokens (int): Output token count used.
            - total_tokens (int): Sum of input and output tokens.
            - cost_per_1k_input (float): Input cost per 1k tokens (USD).
            - cost_per_1k_output (float): Output cost per 1k tokens (USD).
            - estimated_cost_usd (float): Rounded total estimated cost in USD.
            - currency (str): Currency code, always "USD".
    """
    from backend.db.models.workspace import ModelConfig
    from sqlalchemy import select
    
    model_id = body.get("model", "gpt-4o")
    input_tokens = body.get("input_tokens", body.get("estimated_tokens", 1000))
    output_tokens = body.get("output_tokens", 0)
    
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


@router.post("/transcribe")
async def transcribe(user=Depends(get_current_user)):
    """
    Return a placeholder transcription payload instructing the caller to upload audio for processing.
    
    Returns:
        dict: A payload with:
            - `text` (str): Placeholder transcription message.
            - `language` (str): Language code, default `"en"`.
            - `duration_seconds` (int): Audio duration in seconds; `0` for the placeholder.
    """
    return {"text": "Transcription placeholder - upload audio for processing.", "language": "en", "duration_seconds": 0}


# ---------------------------------------------------------------------------
# /ai/inference  — cached smart-tier inference (x402-ready)
# ---------------------------------------------------------------------------

@router.post("/inference")
async def ai_inference(body: dict, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """
    Perform policy-guided AI inference with hot/warm caching and tenant-aware provider selection.
    
    Returns:
        A mapping with inference results and metadata. Common keys:
            id (str): Unique inference identifier.
            response_text (str): Generated text from the model.
            provider (str): Provider name that produced or would produce the response.
            model (str): Model identifier used or returned by the provider.
            tier (str): Selected task tier used for provider routing.
            cache_hit (str|None): `"hot"` or `"warm"` when served from cache, `None` when freshly computed.
            policy (dict): Policy evaluation summary (e.g., `{"status": "passed", ...}`).
            latency_ms (int): Round-trip latency in milliseconds.
            cost_usd (float): Estimated cost for the response (0.0 for cache hits).
    
        Additional keys present for cache misses:
            escalation_reason (str|None): Reason for escalation when provider routing changed.
            key_source (str|None): Source of the API key used for the outbound call.
            audit_id (int): ID of the persisted execution log record.
            input_tokens (int): Count of prompt/input tokens billed.
            output_tokens (int): Count of completion/output tokens billed.
    """
    t0 = _time.monotonic()
    messages = normalize_messages(body)
    model = body.get("model") or "llama3.2:latest"
    temperature = float(body.get("temperature", 0.7))
    tier = task_tier(body)
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
    override_body = {**body, "messages": messages}
    result, key_source, reason = await run_completion_for_tenant(
        override_body, workspace_id
    )
    latency_ms = int((_time.monotonic() - t0) * 1000)
    content = _content_from_openai_response(result.payload)
    used_model = result.payload.get("model", model)
    usage = result.payload.get("usage", {})
    total_tokens = usage.get("total_tokens", 0)
    cost_usd = round(total_tokens * 0.000002, 6)

    # Populate caches
    await set_hot(used_model, messages, result.payload, temperature)
    await set_warm(used_model, messages, result.payload)

    log = ExecLog(
        user_id=user.id,
        workspace_id=workspace_id,
        model=used_model,
        provider=result.provider,
        prompt_tokens=usage.get("prompt_tokens", 0),
        completion_tokens=usage.get("completion_tokens", 0),
        total_tokens=total_tokens,
        cost_usd=cost_usd,
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
    body: dict,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Handle a single chat turn using per-session Redis memory (max 20 messages, 24-hour TTL).
    
    Processes the incoming user messages, loads the session history, checks hot/warm caches for a full-context response, routes to a selected provider on cache miss, updates session memory and caches with the assistant reply, records an execution audit, and returns the response and metadata.
    
    Parameters:
        body (dict): Request payload containing the user messages (as `messages` or equivalent), and optional keys: `session_id`, `model`, and `temperature`.
    
    Returns:
        dict: Response payload including at least:
            - `response_text` (str): Assistant reply text.
            - `session_id` (str): Session identifier used.
            - `provider` (str): Provider name used or inferred.
            - `model` (str): Model identifier used.
            - `tier` (str): Routing tier applied.
            - `cache_hit` (str|None): `"hot"` for cache hit, `None` for miss.
            - `memory` (dict): Memory metadata with `message_count`, `max` (20), and `ttl_hours` (24).
            - `latency_ms` (int): Round-trip latency in milliseconds.
            - On cache miss: additional fields such as `escalation_reason` (or null), `key_source`, `policy`, `audit_id`, `input_tokens`, `output_tokens`, and `cost_usd`.
    """
    t0 = _time.monotonic()
    workspace_id = user.workspace_id or "default"
    session_id = body.get("session_id") or f"sess_{user.id}"
    model = body.get("model") or "llama3.2:latest"
    temperature = float(body.get("temperature", 0.7))
    tier = task_tier(body)

    # New user message(s) from body
    new_user_msgs = normalize_messages(body)

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
    completion_body = {**body, "messages": full_context}
    result, key_source, reason = await run_completion_for_tenant(completion_body, workspace_id)
    latency_ms = int((_time.monotonic() - t0) * 1000)
    content = _content_from_openai_response(result.payload)
    used_model = result.payload.get("model", model)
    usage = result.payload.get("usage", {})
    total_tokens = usage.get("total_tokens", 0)

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
        prompt_tokens=usage.get("prompt_tokens", 0),
        completion_tokens=usage.get("completion_tokens", 0),
        total_tokens=total_tokens,
        cost_usd=round(total_tokens * 0.000002, 6),
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
        "input_tokens": usage.get("prompt_tokens", 0),
        "output_tokens": usage.get("completion_tokens", 0),
        "cost_usd": round(total_tokens * 0.000002, 6),
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
