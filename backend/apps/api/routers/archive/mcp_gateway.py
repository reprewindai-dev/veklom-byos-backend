import os
import json
import logging
import httpx
import re
from datetime import datetime
import uuid
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse

from backend.core.database.database import get_db
from backend.core.security.auth import get_current_user, get_current_user_optional
from backend.core.config.settings import settings
from backend.core.ai.openapi_ingest import OpenAPICompiler
from backend.core.ai.tool_manifest_store import ToolManifestStore
from backend.security.mcp_gateway import EnhancedMCPAPIRuntime

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["MCP Gateway"])

# Helper for registered connections list
SERVERS_STORE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../data/mcp_servers_registry.json"))

_redis_client = None


def _get_redis_client():
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    try:
        import redis
        _redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
        return _redis_client
    except Exception:
        return None

def _save_server_registry(server_id: str, server_data: Dict[str, Any]):
    redis_client = _get_redis_client()
    if redis_client:
        try:
            redis_client.hset("veklom:mcp:servers", server_id, json.dumps(server_data))
            return
        except Exception as e:
            logger.error(f"Redis failed to save server: {e}")

    # Fallback
    os.makedirs(os.path.dirname(SERVERS_STORE_PATH), exist_ok=True)
    store = {}
    if os.path.exists(SERVERS_STORE_PATH):
        try:
            with open(SERVERS_STORE_PATH, "r") as f:
                store = json.load(f)
        except Exception:
            pass
    store[server_id] = server_data
    with open(SERVERS_STORE_PATH, "w") as f:
        json.dump(store, f)

def _get_all_registered_servers() -> Dict[str, Any]:
    redis_client = _get_redis_client()
    if redis_client:
        try:
            raw = redis_client.hgetall("veklom:mcp:servers")
            return {k: json.loads(v) for k, v in raw.items()}
        except Exception:
            pass

    if os.path.exists(SERVERS_STORE_PATH):
        try:
            with open(SERVERS_STORE_PATH, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

@router.post("/mcp/servers")
async def register_mcp_server(body: Dict[str, Any], user=Depends(get_current_user)):
    """Register an external SaaS and compile its OpenAPI spec into MCP manifests."""
    server_id = body.get("server_id")
    name = body.get("name", server_id)
    openapi_url = body.get("openapi_url")
    base_url = body.get("base_url")
    auth_headers = body.get("auth_headers", {})

    if not server_id or not openapi_url or not base_url:
        raise HTTPException(status_code=400, detail="Missing required parameters: server_id, openapi_url, base_url")

    if not re.match(r"^[a-z0-9_-]+$", server_id):
        raise HTTPException(status_code=400, detail="server_id must be lowercase alphanumeric and may contain hyphens/underscores")

    schema = await OpenAPICompiler.fetch_schema(openapi_url)
    if not schema:
        raise HTTPException(status_code=400, detail=f"Failed to fetch OpenAPI schema from: {openapi_url}")

    manifests = OpenAPICompiler.compile_manifest(schema, server_id, openapi_url)
    if not manifests:
        raise HTTPException(status_code=400, detail="No valid REST endpoints found in OpenAPI schema to map into tools.")

    server_data = {
        "server_id": server_id,
        "name": name,
        "openapi_url": openapi_url,
        "base_url": base_url,
        "auth_headers": auth_headers,
        "workspace_id": user.workspace_id or "default",
        "registered_at": datetime.utcnow().isoformat(),
        "tools_count": len(manifests)
    }

    _save_server_registry(server_id, server_data)
    await ToolManifestStore.save_manifests(manifests)

    return {
        "status": "success",
        "message": f"Successfully registered server '{server_id}' with {len(manifests)} tools.",
        "server": server_data
    }

@router.get("/mcp/servers")
async def list_mcp_servers(user=Depends(get_current_user)):
    """List all registered dynamic MCP servers for the current workspace."""
    all_servers = _get_all_registered_servers()
    ws_id = user.workspace_id or "default"
    return [s for s in all_servers.values() if s.get("workspace_id") == ws_id]

@router.get("/mcp/tools")
async def list_mcp_tools(tags: Optional[str] = None, user=Depends(get_current_user)):
    """List curated tools available to the tenant/swarm from the compiled manifest."""
    manifests = await ToolManifestStore.get_all_manifests()
    
    tools = []
    tag_list = tags.split(",") if tags else []
    
    for m in manifests.values():
        if tag_list and not any(t in m.get("tags", []) for t in tag_list):
            continue
        tools.append(m)
        
    return tools

@router.post("/mcp/tools/{tool_name}:invoke")
async def invoke_mcp_tool(tool_name: str, request: Request, user=Depends(get_current_user_optional)):
    """Governed execution gateway for a compiled MCP tool."""
    
    manifest = await ToolManifestStore.get_tool(tool_name)
    if not manifest:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found in manifest catalog.")

    body_bytes = await request.body()
    body_data = {}
    if body_bytes:
        try:
            body_data = json.loads(body_bytes)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid JSON body")
            
    parameters = body_data.get("parameters", {})

    # 1. Zero-Trust & x402 Readiness Verification (Middleware pattern via Dependency)
    runtime = EnhancedMCPAPIRuntime()
    
    gov_req = {
        "nonce": request.headers.get("X-Veklom-Nonce") or f"nonce_{uuid.uuid4()}",
        "connection_id": f"gateway_{tool_name}",
        "agent_id": user.id if user else "anonymous_agent",
        "capability_id": tool_name,
        "payload": parameters,
        "upstream_evidence_hash": request.headers.get("X-Veklom-Evidence-Hash") or "0x" + "0"*64
    }

    gov_response = await runtime.process_request(gov_req)
    if "error" in gov_response:
        code = int(gov_response["error"].get("code", 403))
        return JSONResponse(status_code=code, content=gov_response)

    # 2. Build the Outbound Request using the manifest
    server_id = manifest["server_id"]
    servers = _get_all_registered_servers()
    server = servers.get(server_id)
    
    if not server:
        raise HTTPException(status_code=500, detail=f"Server connection '{server_id}' is missing from registry.")

    # Substitute path templates (e.g. /intercepts/{id})
    path = manifest["path_template"]
    for k, v in parameters.items():
        if f"{{{k}}}" in path:
            path = path.replace(f"{{{k}}}", str(v))
            
    target_url = f"{server['base_url'].rstrip('/')}{path}"
    
    # Filter query parameters and body based on what is NOT in the path
    query_params = {}
    json_body = {}
    
    input_props = manifest["input_schema"].get("properties", {})
    for k, v in parameters.items():
        if f"{{{k}}}" not in manifest["path_template"]:
            # Basic heuristic: if it's a GET, it goes to query. If POST/PUT, if "body" schema implies nesting, put in body.
            if manifest["method"] in ("POST", "PUT", "PATCH"):
                if k == "body":
                    json_body = v
                else:
                    json_body[k] = v
            else:
                query_params[k] = v

    headers = {}
    # Inject configured SaaS authentication headers securely
    for k, v in server.get("auth_headers", {}).items():
        headers[k] = v

    # Execute the HTTP request
    try:
        async with httpx.AsyncClient(timeout=manifest["execution_profile"]["timeout_ms"] / 1000.0) as client:
            resp = await client.request(
                method=manifest["method"],
                url=target_url,
                headers=headers,
                params=query_params,
                json=json_body if manifest["method"] in ("POST", "PUT", "PATCH") else None
            )
            
            resp_headers = {}
            for k, v in resp.headers.items():
                if k.lower() not in ("content-encoding", "transfer-encoding", "content-length"):
                    resp_headers[k] = v

            # Inject VNP & x402 proof headers
            resp_headers["X-VNP-Stake-Result"] = "verified"
            resp_headers["X-Veklom-Receipt-ID"] = gov_response.get("evidence_hash") or f"rcpt_{uuid.uuid4()}"

            return Response(
                content=resp.content,
                status_code=resp.status_code,
                headers=resp_headers
            )
    except Exception as e:
        logger.error(f"Failed to forward request to tool target '{target_url}': {e}")
        raise HTTPException(status_code=502, detail=f"Gateway error: Failed to connect to downstream service. Details: {e}")
