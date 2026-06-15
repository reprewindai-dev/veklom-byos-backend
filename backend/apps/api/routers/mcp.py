"""Model Context Protocol (MCP) Router - Layer 2 of AI Agents Stack 2026"""

import json
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
import httpx
import logging

from backend.core.database.database import get_db
from backend.core.security.auth import get_current_user
from backend.db.models.agent_stack import MCPTool, MCPConnection, Agent, AgentExecution, AgentTrace, SafetyIncident

router = APIRouter(prefix="/api/v1/mcp", tags=["MCP Protocol"])
logger = logging.getLogger(__name__)


class MCPConnectionManager:
    """WebSocket connection manager for real-time MCP communication"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.connection_sessions: Dict[str, str] = {}
    
    async def connect(self, websocket: WebSocket, connection_id: str, session_id: str):
        await websocket.accept()
        self.active_connections[connection_id] = websocket
        self.connection_sessions[connection_id] = session_id
        logger.info(f"MCP WebSocket connected: {connection_id}")
    
    def disconnect(self, connection_id: str):
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
        if connection_id in self.connection_sessions:
            del self.connection_sessions[connection_id]
        logger.info(f"MCP WebSocket disconnected: {connection_id}")
    
    async def send_message(self, connection_id: str, message: Dict[str, Any]):
        if connection_id in self.active_connections:
            websocket = self.active_connections[connection_id]
            await websocket.send_text(json.dumps(message))
    
    async def broadcast_to_session(self, session_id: str, message: Dict[str, Any]):
        for conn_id, ws_session in self.connection_sessions.items():
            if ws_session == session_id and conn_id in self.active_connections:
                await self.send_message(conn_id, message)


manager = MCPConnectionManager()


@router.get("/tools")
async def list_mcp_tools(
    workspace_id: str = None,
    tool_type: str = None,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List available MCP tools"""
    try:
        query = select(MCPTool).where(MCPTool.is_active == True)
        
        # Filter by workspace if specified
        if workspace_id:
            query = query.where(MCPTool.workspace_id == workspace_id)
        else:
            query = query.where(MCPTool.workspace_id == user.workspace_id)
        
        # Filter by tool type if specified
        if tool_type:
            query = query.where(MCPTool.tool_type == tool_type)
        
        result = await db.execute(query)
        tools = result.scalars().all()
        
        return {
            "tools": [
                {
                    "id": tool.id,
                    "name": tool.name,
                    "description": tool.description,
                    "tool_type": tool.tool_type,
                    "protocol_version": tool.protocol_version,
                    "input_schema": tool.input_schema,
                    "output_schema": tool.output_schema,
                    "required_permissions": tool.required_permissions,
                    "safety_level": tool.safety_level,
                    "usage_count": tool.usage_count,
                    "last_used": tool.last_used.isoformat() if tool.last_used else None
                }
                for tool in tools
            ],
            "total_count": len(tools)
        }
        
    except Exception as e:
        logger.error(f"Failed to list MCP tools: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list tools: {str(e)}")


@router.post("/tools/{tool_id}/execute")
async def execute_mcp_tool(
    tool_id: str,
    execution_data: Dict[str, Any],
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Execute an MCP tool with safety checks and tracing"""
    try:
        # Get the tool
        result = await db.execute(
            select(MCPTool).where(
                and_(
                    MCPTool.id == tool_id,
                    MCPTool.workspace_id == user.workspace_id,
                    MCPTool.is_active == True
                )
            )
        )
        tool = result.scalar_one_or_none()
        
        if not tool:
            raise HTTPException(status_code=404, detail="Tool not found")
        
        # Validate input against schema
        if not validate_tool_input(execution_data, tool.input_schema):
            raise HTTPException(status_code=400, detail="Invalid input data")
        
        # Check safety level and permissions
        safety_check = await check_tool_safety(tool, execution_data, user, db)
        if not safety_check["allowed"]:
            raise HTTPException(status_code=403, detail=f"Safety check failed: {safety_check['reason']}")
        
        # Create execution trace
        execution_id = f"exec_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{tool_id[:8]}"
        
        trace = AgentTrace(
            id=f"trace_{execution_id}",
            agent_id=None,  # Can be set if called by an agent
            workspace_id=user.workspace_id,
            execution_id=execution_id,
            trace_type="tool_call",
            input_data=execution_data,
            metadata={
                "tool_id": tool_id,
                "tool_name": tool.name,
                "tool_type": tool.tool_type,
                "user_id": user.id
            }
        )
        db.add(trace)
        
        # Execute the tool
        start_time = datetime.now(timezone.utc)
        
        try:
            result_data = await execute_tool_logic(tool, execution_data)
            
            # Update trace with success
            trace.output_data = result_data
            trace.success = True
            trace.duration_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            
            # Update tool usage stats
            tool.usage_count += 1
            tool.last_used = datetime.now(timezone.utc)
            
            await db.commit()
            
            return {
                "execution_id": execution_id,
                "success": True,
                "result": result_data,
                "tool_info": {
                    "name": tool.name,
                    "type": tool.tool_type,
                    "safety_level": tool.safety_level
                }
            }
            
        except Exception as e:
            # Update trace with error
            trace.success = False
            trace.error_message = str(e)
            trace.duration_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            
            # Update tool error rate
            tool.error_rate = ((tool.error_rate * tool.usage_count) + 1) / (tool.usage_count + 1)
            
            await db.commit()
            
            # Log safety incident if this is a security-related error
            if tool.safety_level in ["restricted", "dangerous"]:
                await log_safety_incident(
                    db=db,
                    agent_id=None,
                    workspace_id=user.workspace_id,
                    execution_id=execution_id,
                    incident_type="tool_execution_error",
                    severity="medium",
                    description=f"Tool {tool.name} failed with security implications: {str(e)}",
                    context_data={
                        "tool_id": tool_id,
                        "error": str(e),
                        "user_id": user.id
                    }
                )
            
            raise HTTPException(status_code=500, detail=f"Tool execution failed: {str(e)}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to execute MCP tool {tool_id}: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Execution failed: {str(e)}")


@router.get("/connections")
async def list_mcp_connections(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List MCP server connections"""
    try:
        result = await db.execute(
            select(MCPConnection).where(
                MCPConnection.workspace_id == user.workspace_id
            )
        )
        connections = result.scalars().all()
        
        return {
            "connections": [
                {
                    "id": conn.id,
                    "server_name": conn.server_name,
                    "server_endpoint": conn.server_endpoint,
                    "status": conn.status,
                    "last_ping": conn.last_ping.isoformat() if conn.last_ping else None,
                    "server_capabilities": conn.server_capabilities,
                    "session_expires": conn.session_expires.isoformat() if conn.session_expires else None
                }
                for conn in connections
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to list MCP connections: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list connections: {str(e)}")


@router.post("/connections/{connection_id}/connect")
async def connect_mcp_server(
    connection_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Connect to an MCP server"""
    try:
        result = await db.execute(
            select(MCPConnection).where(
                and_(
                    MCPConnection.id == connection_id,
                    MCPConnection.workspace_id == user.workspace_id
                )
            )
        )
        connection = result.scalar_one_or_none()
        
        if not connection:
            raise HTTPException(status_code=404, detail="Connection not found")
        
        # Attempt to connect to the MCP server
        async with httpx.AsyncClient() as client:
            try:
                # Send MCP handshake
                handshake_response = await client.post(
                    f"{connection.server_endpoint}/handshake",
                    json={
                        "client_id": connection.client_id,
                        "protocol_version": connection.protocol_version,
                        "capabilities": ["tools", "resources", "prompts"]
                    },
                    timeout=10.0
                )
                
                if handshake_response.status_code == 200:
                    server_info = handshake_response.json()
                    
                    # Update connection status
                    connection.status = "connected"
                    connection.last_ping = datetime.now(timezone.utc)
                    connection.server_capabilities = server_info.get("capabilities", {})
                    connection.session_id = server_info.get("session_id")
                    connection.session_expires = datetime.now(timezone.utc).replace(
                        hour=23, minute=59, second=59
                    )  # End of day
                    
                    await db.commit()
                    
                    return {
                        "success": True,
                        "server_info": server_info,
                        "session_id": connection.session_id
                    }
                else:
                    connection.status = "error"
                    await db.commit()
                    raise HTTPException(
                        status_code=400, 
                        detail=f"Server handshake failed: {handshake_response.text}"
                    )
                    
            except httpx.RequestError as e:
                connection.status = "error"
                await db.commit()
                raise HTTPException(status_code=400, detail=f"Failed to connect to server: {str(e)}")
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to connect MCP server {connection_id}: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Connection failed: {str(e)}")


@router.websocket("/ws/{connection_id}")
async def mcp_websocket_endpoint(
    websocket: WebSocket,
    connection_id: str,
    db: AsyncSession = Depends(get_db)
):
    """WebSocket endpoint for real-time MCP communication"""
    # For WebSocket, we need to handle auth differently
    # This is a simplified version - in production, you'd want proper WebSocket auth
    
    try:
        # Verify connection exists
        result = await db.execute(
            select(MCPConnection).where(MCPConnection.id == connection_id)
        )
        connection = result.scalar_one_or_none()
        
        if not connection:
            await websocket.close(code=4004, reason="Connection not found")
            return
        
        session_id = f"mcp_session_{connection_id}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        await manager.connect(websocket, connection_id, session_id)
        
        try:
            while True:
                # Receive message from client
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Process MCP message
                response = await process_mcp_message(message, connection, db)
                
                # Send response back
                await manager.send_message(connection_id, response)
                
        except WebSocketDisconnect:
            manager.disconnect(connection_id)
            
    except Exception as e:
        logger.error(f"MCP WebSocket error: {str(e)}")
        await websocket.close(code=4000, reason="Internal server error")


# Helper functions
def validate_tool_input(data: Dict[str, Any], schema: Dict[str, Any]) -> bool:
    """Validate tool input against JSON schema"""
    # Simplified validation - in production, use jsonschema library
    required_fields = schema.get("required", [])
    
    for field in required_fields:
        if field not in data:
            return False
    
    return True


async def check_tool_safety(tool: MCPTool, data: Dict[str, Any], user, db: AsyncSession) -> Dict[str, Any]:
    """Check if tool execution is safe for this user"""
    # Check user permissions
    if tool.required_permissions:
        user_permissions = getattr(user, 'permissions', [])
        for permission in tool.required_permissions:
            if permission not in user_permissions:
                return {
                    "allowed": False,
                    "reason": f"Missing required permission: {permission}"
                }
    
    # Check safety level
    if tool.safety_level == "dangerous":
        # Dangerous tools require admin approval
        if not getattr(user, 'is_admin', False):
            return {
                "allowed": False,
                "reason": "Dangerous tools require admin approval"
            }
    
    elif tool.safety_level == "restricted":
        # Restricted tools need special handling
        # Could implement rate limiting, approval workflows, etc.
        pass
    
    return {"allowed": True}


async def execute_tool_logic(tool: MCPTool, data: Dict[str, Any]) -> Dict[str, Any]:
    """Execute the actual tool logic based on tool type"""
    
    from backend.core.services.tool_execution_service import get_tool_execution_service
    
    tool_service = get_tool_execution_service()
    
    if tool.tool_type == "filesystem":
        return await tool_service.execute_filesystem_tool(data)
    elif tool.tool_type == "database":
        return await tool_service.execute_database_tool(data)
    elif tool.tool_type == "api":
        return await tool_service.execute_api_tool(data)
    elif tool.tool_type == "browser":
        return await tool_service.execute_browser_tool(data)
    else:
        # Generic tool execution
        return await tool_service.execute_custom_tool(data)




async def process_mcp_message(message: Dict[str, Any], connection: MCPConnection, db: AsyncSession) -> Dict[str, Any]:
    """Process incoming MCP WebSocket message"""
    message_type = message.get("type", "unknown")
    
    if message_type == "ping":
        return {
            "type": "pong",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    elif message_type == "tool_call":
        # Handle tool call via WebSocket
        tool_id = message.get("tool_id")
        tool_data = message.get("data", {})
        
        # Execute the tool (similar to HTTP endpoint)
        try:
            result = await execute_tool_logic_by_id(tool_id, tool_data, db)
            return {
                "type": "tool_response",
                "success": True,
                "result": result
            }
        except Exception as e:
            return {
                "type": "tool_response",
                "success": False,
                "error": str(e)
            }
    
    else:
        return {
            "type": "error",
            "message": f"Unknown message type: {message_type}"
        }


async def execute_tool_logic_by_id(tool_id: str, data: Dict[str, Any], db: AsyncSession) -> Dict[str, Any]:
    """Execute tool by ID (helper for WebSocket)"""
    result = await db.execute(select(MCPTool).where(MCPTool.id == tool_id))
    tool = result.scalar_one_or_none()
    
    if not tool:
        raise ValueError("Tool not found")
    
    return await execute_tool_logic(tool, data)


async def log_safety_incident(
    db: AsyncSession,
    agent_id: Optional[str],
    workspace_id: str,
    execution_id: str,
    incident_type: str,
    severity: str,
    description: str,
    context_data: Dict[str, Any]
):
    """Log a safety/security incident"""
    incident = SafetyIncident(
        id=f"incident_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{execution_id[:8]}",
        agent_id=agent_id,
        workspace_id=workspace_id,
        execution_id=execution_id,
        incident_type=incident_type,
        severity=severity,
        description=description,
        context_data=context_data,
        detected_by="system_monitor"
    )
    
    db.add(incident)
    await db.commit()
    
    logger.warning(f"Safety incident logged: {incident_type} - {description}")
