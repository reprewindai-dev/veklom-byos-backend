"""LLM Inference Engine Router — aligned to Section 4, 5, and 6 of the User Manual."""

import hmac
import hashlib
import time
from datetime import datetime, timezone
import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config.settings import settings
from backend.core.database.database import get_db
from backend.core.security.auth import get_current_user, get_current_user_or_api_key
from backend.core.ai.provider_router import run_completion, stream_completion
from backend.core.llm.circuit_breaker import CircuitBreaker
from backend.core.memory.conversation import ConversationMemory
from backend.core.security.wallet_guard import token_deduction_guard
from backend.db.models.ai import ExecutionLog, AIAuditLog

router = APIRouter(tags=["LLM Inference Engine"])

class ExecRequest(BaseModel):
    prompt: str
    model: Optional[str] = None
    conversation_id: Optional[str] = None
    use_memory: bool = True
    max_tokens: Optional[int] = 2048
    temperature: Optional[float] = 0.7

@router.post("/v1/exec")
async def exec_prompt(
    body: ExecRequest,
    request: Request,
    user=Depends(get_current_user_or_api_key),
    db: AsyncSession = Depends(get_db),
    _wallet=Depends(token_deduction_guard)
):
    start_time = time.time()

    # 1. Resolve model
    model = body.model or getattr(settings, "LLM_MODEL_DEFAULT", "qwen2.5:3b")
    
    # 2. Memory Context
    history = []
    if body.conversation_id and body.use_memory:
        history = await ConversationMemory.get_history(user.workspace_id, body.conversation_id)

    # 3. Format Prompt with History
    messages = []
    for h in history:
        messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": body.prompt})
    
    # 4. Circuit Breaker & Fallback
    cb = CircuitBreaker("ollama")
    cb_state = await cb.get_state()
    
    provider = "ollama"
    response_text = ""
    prompt_tokens = 0
    completion_tokens = 0

    # Calculate simple tokens for backup if provider doesn't return usage
    approx_prompt_tokens = sum(len(m["content"].split()) for m in messages) * 2

    if cb_state in ("CLOSED", "HALF_OPEN"):
        # Attempt Local Ollama
        try:
            ollama_url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/chat"
            payload = {
                "model": model,
                "messages": messages,
                "stream": False,
                "options": {
                    "num_predict": body.max_tokens,
                    "temperature": body.temperature
                }
            }
            timeout = float(getattr(settings, "LLM_TIMEOUT_SECONDS", 60))
            async with httpx.AsyncClient(timeout=timeout) as client:
                res = await client.post(ollama_url, json=payload)

            if res.status_code == 200:
                data = res.json()
                response_text = data.get("message", {}).get("content", "")
                prompt_tokens = data.get("prompt_eval_count") or data.get("prompt_tokens") or approx_prompt_tokens
                completion_tokens = data.get("eval_count") or data.get("completion_tokens") or (len(response_text.split()) * 2)
                await cb.record_success()
            else:
                raise Exception(f"Ollama returned status {res.status_code}")
        except Exception as e:
            await cb.record_failure()
            # Try fallback to Groq if allowed
            fallback = getattr(settings, "LLM_FALLBACK", "groq")
            if fallback == "groq" and settings.GROQ_API_KEY:
                provider = "groq"
            else:
                raise HTTPException(status_code=503, detail=f"Local Ollama failed and no fallback available: {str(e)}")
    else:
        # Circuit is OPEN, proceed directly to Groq fallback
        provider = "groq"
        
    if provider == "groq":
        # Call Groq Chat Completions
        try:
            groq_url = "https://api.groq.com/openai/v1/chat/completions"
            groq_model = getattr(settings, "GROQ_MODEL", "llama-3.1-8b-instant")
            headers = {
                "Authorization": f"Bearer {settings.GROQ_API_KEY.strip()}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": groq_model,
                "messages": messages,
                "stream": False,
                "max_tokens": body.max_tokens,
                "temperature": body.temperature
            }
            async with httpx.AsyncClient(timeout=60.0) as client:
                res = await client.post(groq_url, headers=headers, json=payload)

            if res.status_code == 200:
                data = res.json()
                response_text = data["choices"][0]["message"]["content"]
                usage = data.get("usage", {})
                prompt_tokens = usage.get("prompt_tokens", approx_prompt_tokens)
                completion_tokens = usage.get("completion_tokens", len(response_text.split()) * 2)
            else:
                raise Exception(f"Groq API returned status {res.status_code}")
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Groq fallback failed: {str(e)}")

    latency_ms = int((time.time() - start_time) * 1000)
    total_tokens = prompt_tokens + completion_tokens

    # 5. Save Memory
    if body.conversation_id and body.use_memory:
        new_msgs = [
            {"role": "user", "content": body.prompt},
            {"role": "assistant", "content": response_text}
        ]
        await ConversationMemory.add_messages(user.workspace_id, body.conversation_id, new_msgs)
        
    # Calculate Cost (Ollama is free, Groq is cheap)
    cost = 0.0
    if provider == "groq":
        cost = (prompt_tokens * 0.00005 + completion_tokens * 0.0001) / 1000
        
    # 6. Immutable Audit & Execution Logging
    hmac_hash = hmac.new(
        settings.JWT_SECRET_KEY.encode(),
        response_text.encode(),
        hashlib.sha256
    ).hexdigest()

    exec_log = ExecutionLog(
        workspace_id=user.workspace_id,
        user_id=user.id,
        model=model,
        provider=provider,
        input_tokens=prompt_tokens,
        output_tokens=completion_tokens,
        cost=cost,
        latency_ms=latency_ms
    )
    db.add(exec_log)
    await db.flush()

    audit_log = AIAuditLog(
        workspace_id=user.workspace_id,
        operation_type="inference",
        provider=provider,
        model=model,
        input_tokens=prompt_tokens,
        output_tokens=completion_tokens,
        cost=cost,
        latency_ms=latency_ms,
        hmac_hash=hmac_hash
    )
    db.add(audit_log)
    await db.commit()
    
    return {
        "response": response_text,
        "provider": provider,
        "model": model,
        "conversation_id": body.conversation_id,
        "tenant_id": user.workspace_id,
        "log_id": audit_log.id,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "latency_ms": latency_ms
    }

# ERC-8021 / Veklom Production Stream Completer compatible endpoints
@router.post("/chat/completions")
@router.post("/ai/exec")
async def exec_stream(
    request: Request,
    user=Depends(get_current_user),
    _wallet=Depends(token_deduction_guard)
):
    body = await request.json()
    stream = body.get("stream", True)

    if not stream:
        result = await run_completion(body, stream=False)
        return result.payload

    async def event_generator():
        async for line in stream_completion(body):
            yield line

    return StreamingResponse(event_generator(), media_type="text/event-stream")
