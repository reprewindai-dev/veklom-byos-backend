"""MCP server that exposes the Veklom TOOL_MAP over the Model Context Protocol."""
from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.core.llm.tool_schema import validate_tool_call
from backend.core.tools import TOOL_MAP  # existing tool registry

router = APIRouter(prefix="/mcp", tags=["mcp"])


class MCPToolCallRequest(BaseModel):
    tool: str
    parameters: dict[str, Any] = {}
    request_id: str | None = None


class MCPToolCallResponse(BaseModel):
    request_id: str | None
    tool: str
    result: Any
    error: str | None = None


@router.get("/tools")
async def list_tools() -> dict:
    """Return all registered tools in MCP schema format."""
    tools = []
    for name, fn in TOOL_MAP.items():
        schema = getattr(fn, "__tool_schema__", None)
        tools.append({"name": name, "description": getattr(fn, "__doc__", ""), "schema": schema})
    return {"tools": tools}


@router.post("/call", response_model=MCPToolCallResponse)
async def call_tool(req: MCPToolCallRequest) -> MCPToolCallResponse:
    """Invoke a registered tool by name with validated parameters."""
    if req.tool not in TOOL_MAP:
        raise HTTPException(status_code=404, detail=f"Tool '{req.tool}' not found")
    try:
        validated = validate_tool_call(req.tool, req.parameters)
        result = await TOOL_MAP[req.tool](**validated)
        return MCPToolCallResponse(request_id=req.request_id, tool=req.tool, result=result)
    except Exception as exc:
        return MCPToolCallResponse(request_id=req.request_id, tool=req.tool, result=None, error=str(exc))
