"""webMCP-compatible SSE + HTTP transport for cAPI."""

import httpx
import json
from typing import Dict, Any, AsyncGenerator

class WebCAPITransport:
    """
    Handles communication via webcAPI protocol.
    Wraps standard HTTP and SSE with governance requirements.
    """
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    async def call_tool(self, intent: Dict[str, Any], token: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            headers = {"X-cAPI-Intent": token}
            resp = await client.post(f"{self.base_url}/mcp/call", json=intent, headers=headers)
            resp.raise_for_status()
            return resp.json()

    async def stream_events(self) -> AsyncGenerator[Dict[str, Any], None]:
        async with httpx.AsyncClient() as client:
            async with client.stream("GET", f"{self.base_url}/mcp/stream") as resp:
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        yield json.loads(line[6:])
