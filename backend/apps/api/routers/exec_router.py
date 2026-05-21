"""SSE streaming exec endpoint (OpenAI-compatible)."""

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from backend.core.ai.provider_router import run_completion, stream_completion
from backend.core.security.auth import get_current_user
from backend.core.security.wallet_guard import token_deduction_guard
from backend.core.security.entitlements import require_entitlement

router = APIRouter(
    tags=["AI Exec SSE"],
    dependencies=[
        Depends(get_current_user),
        Depends(token_deduction_guard),
        Depends(require_entitlement("pro"))
    ]
)


@router.post("/v1/exec")
async def exec_stream(request: Request, user=Depends(get_current_user)):
    body = await request.json()
    stream = body.get("stream", True)

    if not stream:
        result = await run_completion(body, stream=False)
        return result.payload

    async def event_generator():
        async for line in stream_completion(body):
            yield line

    return StreamingResponse(event_generator(), media_type="text/event-stream")
