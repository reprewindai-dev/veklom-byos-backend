"""GET/POST /capi/mcp — webMCP-compatible transport."""

from fastapi import APIRouter, Request, Header
from fastapi.responses import StreamingResponse
from typing import Optional
import json
import asyncio

router = APIRouter(tags=["webcAPI"])

@router.post("/mcp/call")
async def mcp_call(
    request: Request,
    x_capi_intent: str = Header(..., description="Signed ExecutionIntent token")
):
    """
    Governed tool execution.
    Replaces raw MCP call by requiring a valid intent token.
    """
    # Logic to execute tool via governed transport
    return {"status": "success", "result": "..."}

@router.get("/mcp/stream")
async def mcp_stream():
    """
    SSE stream of execution events + evidence.
    """
    async def event_generator():
        while True:
            # Stream events
            yield f"data: {json.dumps({'type': 'execution_event', 'msg': '...'})}\n\n"
            await asyncio.sleep(1)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.get("/.well-known/webcapi.json")
async def webcapi_manifest():
    """Capability manifest with PGL requirements."""
    return {
        "transport": "webcAPI/1.0",
        "pgl_required": True,
        "capabilities": [
            {"name": "github.read", "risk": "low"},
            {"name": "wallet.pay", "risk": "high"}
        ]
    }
