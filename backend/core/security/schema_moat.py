"""
Amphoteric Schema Moat — Dynamic Compilation & Depth Verification.

Protects against recursive schema injection attacks and coordinates
in-process Pydantic-to-MCP JSON-Schema compile targets.
"""

import logging
from typing import Any, Dict, Type, Optional
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

# Avoid circular imports by deferred imports of database models
logger = logging.getLogger(__name__)

def verify_schema_depth(data: Any, max_depth: int = 6, current_depth: int = 1) -> None:
    """
    Recursively audits dictionaries and lists to ensure nested depth does not exceed
    max_depth. Protects against stack-overflow / CPU-starvation attacks from indirect
    prompt injection (circular references).
    """
    if current_depth > max_depth:
        logger.error(f"[SchemaMoat] Payload exceeded maximum nested depth cap: {current_depth} > {max_depth}")
        raise ValueError(f"Schema depth limit exceeded (capped at max nested depth of {max_depth})")

    if isinstance(data, dict):
        for k, v in data.items():
            verify_schema_depth(v, max_depth, current_depth + 1)
    elif isinstance(data, list):
        for item in data:
            verify_schema_depth(item, max_depth, current_depth + 1)

async def register_pydantic_as_mcp_tool(
    db: AsyncSession,
    workspace_id: str,
    name: str,
    description: str,
    tool_type: str,
    model: Type[BaseModel],
    safety_level: str = "safe"
) -> Any:
    """
    Dynamic Compiler: Compiles any Pydantic model directly into an active database MCPTool schema.
    Collapses the proxy boundary: OpenAPI endpoint schemas are translated to MCP JSON Schema dynamically.
    Ensures complete, absolute synchronization.
    """
    from backend.db.models.agent_stack import MCPTool
    
    # 1. Generate OpenAPI-compatible JSON Schema from Pydantic
    try:
        # Pydantic v2 compatible
        schema = model.model_json_schema()
    except AttributeError:
        # Fallback for Pydantic v1
        schema = model.schema()

    # 2. Query for existing tool
    stmt = select(MCPTool).where(MCPTool.workspace_id == workspace_id, MCPTool.name == name)
    res = await db.execute(stmt)
    existing = res.scalar_one_or_none()

    if existing:
        logger.info(f"[SchemaMoat] Updating dynamic schema for tool: '{name}' in workspace {workspace_id}")
        existing.description = description
        existing.input_schema = schema
        existing.tool_type = tool_type
        existing.safety_level = safety_level
        db.add(existing)
        tool = existing
    else:
        logger.info(f"[SchemaMoat] Registering new dynamic compiled tool: '{name}' in workspace {workspace_id}")
        tool = MCPTool(
            id=f"mcp_{uuid.uuid4().hex[:12]}",
            workspace_id=workspace_id,
            name=name,
            description=description,
            tool_type=tool_type,
            input_schema=schema,
            safety_level=safety_level,
            is_active=True
        )
        db.add(tool)

    await db.flush()
    return tool
