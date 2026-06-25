"""
Amphoteric Sensing Middleware — The "pH" Meter of the Veklom Sovereign Runtime.

Detects the protocol environment (pH) of incoming requests to dynamically
stabilize the "cocrystal" of application state and agent tool-sets.

Aligned with the 2026 Amphoteric Paradigm: Unifying WebMCP, MCP, and Veklom
for Sovereign Agentic Edge Architectures.
"""

import time
import logging
from enum import Enum
from typing import Optional
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = logging.getLogger(__name__)

class AmphotericProtocol(str, Enum):
    WEB_UI = "web_ui"           # Traditional Human GUI (pH 7.0 - Neutral)
    WEBMCP = "webmcp"           # Browser-Native AI Agent (pH 8.0 - Basic)
    MCP_RPC = "mcp_rpc"         # Headless Agent / JSON-RPC (pH 6.0 - Acidic)
    REST_API = "rest_api"       # Standard Machine Client (pH 7.5 - Slightly Basic)

class AmphotericSensingMiddleware(BaseHTTPMiddleware):
    """
    Senses the protocol pH and attaches the identity to the request state.
    COLLAPSES the proxy boundary by allowing the runtime to adapt its response
    format dynamically.
    """

    async def dispatch(self, request: Request, call_next):
        protocol = self._sense_protocol(request)

        # Attach protocol to request state for downstream "Amphoteric" adapters
        request.state.amphoteric_protocol = protocol

        # Log sensing event (pH measurement)
        # logger.debug(f"[Amphoteric] Sensed protocol: {protocol} for path: {request.url.path}")

        start_time = time.time()
        response: Response = await call_next(request)
        duration = time.time() - start_time

        # Inject Amphoteric Headers (Cocrystal Stabilization)
        response.headers["X-Amphoteric-Protocol"] = protocol.value
        response.headers["X-Amphoteric-pH"] = self._protocol_to_ph(protocol)

        return response

    def _sense_protocol(self, request: Request) -> AmphotericProtocol:
        """
        Heuristic-based protocol sensing.
        Determines the client's "pH" level based on headers, content-type, and metadata.
        """
        headers = request.headers
        content_type = headers.get("content-type", "").lower()
        user_agent = headers.get("user-agent", "").lower()

        # 1. Sense Headless MCP (JSON-RPC / Acidic)
        # Headless agents typically use specific MCP headers or JSON-RPC content types
        if (
            "application/json-rpc" in content_type or
            headers.get("x-mcp-version") or
            headers.get("x-mcp-protocol")
        ):
            return AmphotericProtocol.MCP_RPC

        # 2. Sense WebMCP (Browser-Native AI / Basic)
        # Chrome 146+ WebMCP interactions often carry specific origin/sec headers
        # or the experimental document.modelContext signal
        if (
            headers.get("x-webmcp-enabled") == "true" or
            "webmcp" in user_agent or
            headers.get("sec-webmcp-context")
        ):
            return AmphotericProtocol.WEBMCP

        # 3. Sense REST API (Machine-to-Machine / Slightly Basic)
        # Identified by non-browser User-Agents and typical API paths
        if (
            request.url.path.startswith("/api/v1") and
            ("mozilla" not in user_agent and "chrome" not in user_agent)
        ):
            return AmphotericProtocol.REST_API

        # 4. Default: Web UI (Human GUI / Neutral)
        return AmphotericProtocol.WEB_UI

    def _protocol_to_ph(self, protocol: AmphotericProtocol) -> str:
        """Metaphorical pH mapping for the Amphoteric runtime."""
        mapping = {
            AmphotericProtocol.MCP_RPC: "6.0",
            AmphotericProtocol.WEB_UI: "7.0",
            AmphotericProtocol.REST_API: "7.5",
            AmphotericProtocol.WEBMCP: "8.0",
        }
        return mapping.get(protocol, "7.0")
