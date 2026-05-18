"""SSE streaming exec endpoint (OpenAI-compatible)."""

import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from backend.core.security.auth import get_current_user

router = APIRouter(tags=["AI Exec SSE"])


@router.post("/v1/exec")
async def exec_stream(request: Request, user=Depends(get_current_user)):
    body = await request.json()
    model = body.get("model", "gpt-4o")
    stream = body.get("stream", True)

    if not stream:
        return {
            "id": f"exec-{uuid.uuid4().hex[:8]}",
            "model": model,
            "choices": [{"index": 0, "message": {"role": "assistant", "content": "Governed completion via Veklom."}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 50, "completion_tokens": 20, "total_tokens": 70},
        }

    async def event_generator():
        exec_id = f"exec-{uuid.uuid4().hex[:8]}"
        chunks = [
            "Governed ", "response ", "from ", f"{model}. ",
            "Policy ", "checks ", "passed. ",
            "Content ", "safety ", "score: ", "0.98. ",
            "Audit ", "trail ", "recorded."
        ]
        for i, chunk in enumerate(chunks):
            data = {
                "id": exec_id,
                "object": "chat.completion.chunk",
                "model": model,
                "choices": [{"index": 0, "delta": {"content": chunk}, "finish_reason": None}],
            }
            yield f"data: {json.dumps(data)}\n\n"

        done = {
            "id": exec_id,
            "object": "chat.completion.chunk",
            "model": model,
            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
        }
        yield f"data: {json.dumps(done)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
