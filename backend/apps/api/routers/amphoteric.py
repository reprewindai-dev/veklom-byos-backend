"""
Amphoteric Router — Unified Agentic Interface (The Zwitterionic Primitive).

SPEAKS: JSON (REST), WebMCP (Browser Agent), MCP RPC (Headless Agent).
COLLAPSES: Proxy boundary into a single compiled application process.

Aligned with the 2026 Amphoteric Paradigm: Unifying WebMCP, MCP, and Veklom
for Sovereign Agentic Edge Architectures in Quinte West.
"""

import json
import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database.database import get_db
from backend.core.security.auth import get_current_user
from backend.core.config.settings import settings
from backend.core.middleware.amphoteric import AmphotericProtocol
from backend.core.services.tool_execution_service import get_tool_execution_service
from backend.db.models.agent_stack import MCPTool

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/amphoteric", tags=["Amphoteric Unified Protocol"])

def _handle_error(protocol: AmphotericProtocol, message: str, status_code: int, rpc_id: Any = None):
    if protocol == AmphotericProtocol.MCP_RPC:
        return {
            "jsonrpc": "2.0",
            "id": rpc_id,
            "error": {"code": -32000, "message": message}
        }
    else:
        raise HTTPException(status_code=status_code, detail=message)

@router.get("/discover")
async def amphoteric_discovery(
    request: Request,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Unified Tool Discovery.
    Senses protocol (WebUI, WebMCP, or MCP_RPC) and serves tools in the
    client's native pH level.
    """
    protocol = getattr(request.state, "amphoteric_protocol", AmphotericProtocol.REST_API)
    node_type = settings.AMPHOTERIC_NODE_TYPE

    # 1. Fetch real tools from DB
    from sqlalchemy import select
    result = await db.execute(select(MCPTool).where(MCPTool.is_active == True))
    db_tools = result.scalars().all()

    # 2. Adapt tool list based on protocol (Cocrystal Stabilization)
    if protocol == AmphotericProtocol.WEBMCP:
        # Browser-native WebMCP tools (using document.modelContext schema)
        return {
            "protocol": "WebMCP/1.0 (Amphoteric)",
            "node_context": node_type,
            "tools": [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.input_schema,
                    "webmcp_metadata": {
                        "imperative_api": True,
                        "untrusted_content_hint": tool.safety_level == "dangerous"
                    }
                }
                for tool in db_tools
            ]
        }

    elif protocol == AmphotericProtocol.MCP_RPC:
        # Headless MCP JSON-RPC tools
        return {
            "jsonrpc": "2.0",
            "result": {
                "tools": [
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "inputSchema": tool.input_schema
                    }
                    for tool in db_tools
                ]
            }
        }

    else:
        # Standard REST/UI response
        return {
            "status": "operational",
            "protocol_detected": protocol,
            "node_type": node_type,
            "available_tools": [tool.name for tool in db_tools],
            "total_count": len(db_tools)
        }

@router.post("/call")
async def amphoteric_call(
    request: Request,
    call_data: Dict[str, Any],
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Unified Tool Execution.
    The "pH-balanced" execution gate that handles direct tool calls from
    both browser agents and headless servers.
    """
    protocol = getattr(request.state, "amphoteric_protocol", AmphotericProtocol.REST_API)
    tool_name = call_data.get("name") or call_data.get("method")
    params = call_data.get("arguments") or call_data.get("params") or {}

    if not tool_name:
        raise HTTPException(status_code=400, detail="Missing tool name or method")

    # 1. Fetch the tool
    from sqlalchemy import select, and_
    result = await db.execute(
        select(MCPTool).where(
            and_(
                MCPTool.name == tool_name,
                MCPTool.is_active == True
            )
        )
    )
    tool = result.scalar_one_or_none()

    if not tool:
        return _handle_error(protocol, f"Tool '{tool_name}' not found", 404)

    # 2. Execute via real ToolExecutionService
    tool_service = get_tool_execution_service()
    start_time = datetime.now(timezone.utc)

    try:
        # Stabilization Buffer (metaphorical pH stabilization)
        # In Quinte West Starlink nodes, we buffer execution to ensure "cocrystal" alignment
        if settings.AMPHOTERIC_NODE_TYPE == "EDGE_RURAL":
            await asyncio.sleep(settings.AMPHOTERIC_STABILIZATION_MS / 1000.0)

        # Actual execution logic (routing based on tool type)
        execution_payload = {**params, "tool_name": tool_name}

        if tool.tool_type == "filesystem":
            result_data = await tool_service.execute_filesystem_tool(execution_payload)
        elif tool.tool_type == "database":
            result_data = await tool_service.execute_database_tool(execution_payload)
        elif tool.tool_type == "api":
            result_data = await tool_service.execute_api_tool(execution_payload)
        elif tool.tool_type == "browser":
            result_data = await tool_service.execute_browser_tool(execution_payload)
        else:
            result_data = await tool_service.execute_custom_tool(execution_payload)

        # 3. Adapt response format (Cocrystal Stabilization)
        if protocol == AmphotericProtocol.MCP_RPC:
            return {
                "jsonrpc": "2.0",
                "id": call_data.get("id"),
                "result": {
                    "content": [{"type": "text", "text": json.dumps(result_data)}],
                    "isError": not result_data.get("success", True)
                }
            }

        elif protocol == AmphotericProtocol.WEBMCP:
            return {
                "status": "success" if result_data.get("success", True) else "error",
                "tool": tool_name,
                "output": result_data,
                "metadata": {
                    "node": settings.AMPHOTERIC_NODE_TYPE,
                    "latency_ms": int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
                }
            }

        else:
            return result_data

    except Exception as e:
        logger.error(f"[Amphoteric] Execution failed for {tool_name}: {str(e)}")
        return _handle_error(protocol, str(e), 500, call_data.get("id"))
