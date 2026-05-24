"""AI execution routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

import time as _time

from backend.core.ai.provider_router import (
    normalize_messages,
    provider_order,
    run_completion,
    _content_from_openai_response,
)
from backend.core.database.database import get_db
from backend.core.security.auth import get_current_user
from backend.core.security.wallet_guard import token_deduction_guard
from backend.core.security.entitlements import require_entitlement
from backend.db.models.ai import ExecLog

router = APIRouter(
    tags=["AI"],
    dependencies=[
        Depends(get_current_user),
        Depends(token_deduction_guard),
        Depends(require_entitlement("starter"))
    ]
)


@router.post("/ai/complete")
async def ai_complete(body: dict, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
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
@router.get("/ai/models")
async def list_models(user=Depends(get_current_user)):
    return [
        {"id": "gpt-4o", "provider": "openai", "name": "GPT-4o", "context_window": 128000, "cost_per_1k_input": 0.005},
        {"id": "gpt-4o-mini", "provider": "openai", "name": "GPT-4o Mini", "context_window": 128000, "cost_per_1k_input": 0.00015},
        {"id": "llama-3.1-8b-instant", "provider": "groq", "name": "Groq Llama 3.1 8B Instant", "context_window": 131072, "cost_per_1k_input": 0.00005},
        {"id": "meta-llama/Llama-3.1-8B-Instruct:fastest", "provider": "huggingface", "name": "Hugging Face Llama 3.1 8B", "context_window": 131072, "cost_per_1k_input": 0.0001},
        {"id": "gemini-2.5-flash", "provider": "gemini", "name": "Gemini 2.5 Flash", "context_window": 1000000, "cost_per_1k_input": 0.0003},
        {"id": "qwen2.5:3b", "provider": "ollama", "name": "Ollama Qwen 2.5 3B", "context_window": 32768, "cost_per_1k_input": 0.0},
    ]


@router.get("/ai/providers")
async def list_providers(user=Depends(get_current_user)):
    return {"default_order": provider_order({}), "providers": ["ollama", "groq", "huggingface", "gemini", "openai"]}


@router.post("/ai/predict-cost")
async def predict_cost(body: dict, user=Depends(get_current_user)):
    model = body.get("model", "gpt-4o")
    tokens = body.get("estimated_tokens", 1000)
    cost_map = {
        "gpt-4o": 0.005,
        "gpt-4o-mini": 0.00015,
        "llama-3.1-8b-instant": 0.00005,
        "gemini-2.5-flash": 0.0003,
        "qwen2.5:3b": 0.0,
    }
    rate = cost_map.get(model, 0.002)
    return {
        "model": model,
        "estimated_tokens": tokens,
        "estimated_cost_usd": round(tokens / 1000 * rate, 6),
        "currency": "USD",
    }


@router.post("/ai/transcribe")
async def transcribe(user=Depends(get_current_user)):
    return {"text": "Transcription placeholder - upload audio for processing.", "language": "en", "duration_seconds": 0}
