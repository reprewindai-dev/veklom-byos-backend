import os
import json
import logging
import httpx
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database.database import get_db
from backend.core.security.auth import get_current_user, get_current_user_optional
from backend.core.config.settings import settings
from backend.core.ai.mcp_connector import OpenAPItoMCPTranslator
from backend.security.mcp_gateway import EnhancedMCPAPIRuntime

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["MCP Proxy"])

# Local JSON store fallback path
SERVERS_STORE_PATH = "/app/data/mcp_servers.json"

def _get_redis_client():
    """Access the shared redis client if available."""
    try:
        import redis
        return redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
    except Exception:
        return None

def _save_server_to_store(server_id: str, server_data: Dict[str, Any]):
    """Save server definition to Redis or JSON file fallback."""
    redis_client = _get_redis_client()
    if redis_client:
        try:
            redis_client.hset("veklom:mcp:servers", server_id, json.dumps(server_data))
            return
        except Exception as e:
            logger.error(f"Redis failed to save server: {e}")

    # Fallback to local JSON
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

def get_all_registered_servers() -> Dict[str, Any]:
    """Retrieve all custom registered MCP servers."""
    redis_client = _get_redis_client()
    if redis_client:
        try:
            raw_data = redis_client.hgetall("veklom:mcp:servers")
            return {k: json.loads(v) for k, v in raw_data.items()}
        except Exception as e:
            logger.error(f"Redis failed to retrieve servers: {e}")

    # Fallback to local JSON
    if os.path.exists(SERVERS_STORE_PATH):
        try:
            with open(SERVERS_STORE_PATH, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def _delete_server_from_store(server_id: str):
    """Delete server from store."""
    redis_client = _get_redis_client()
    if redis_client:
        try:
            redis_client.hdel("veklom:mcp:servers", server_id)
            return
        except Exception as e:
            logger.error(f"Redis failed to delete server: {e}")

    # Fallback to local JSON
    if os.path.exists(SERVERS_STORE_PATH):
        try:
            with open(SERVERS_STORE_PATH, "r") as f:
                store = json.load(f)
            if server_id in store:
                del store[server_id]
                with open(SERVERS_STORE_PATH, "w") as f:
                    json.dump(store, f)
        except Exception:
            pass


@router.post("/mcp/servers")
async def register_mcp_server(body: Dict[str, Any], user=Depends(get_current_user)):
    """Register an external SaaS as a dynamic MCP server using its OpenAPI URL."""
    server_id = body.get("server_id")
    name = body.get("name", server_id)
    openapi_url = body.get("openapi_url")
    base_url = body.get("base_url")
    auth_headers = body.get("auth_headers", {}) # Optional key-value header overrides

    if not server_id or not openapi_url or not base_url:
        raise HTTPException(status_code=400, detail="Missing required parameters: server_id, openapi_url, base_url")

    # Validate server_id format
    if not re.match(r"^[a-z0-9_-]+$", server_id):
        raise HTTPException(status_code=400, detail="server_id must be lowercase alphanumeric and may contain hyphens/underscores")

    # Try fetching and parsing the schema
    schema = await OpenAPItoMCPTranslator.fetch_schema(openapi_url)
    if not schema:
        raise HTTPException(status_code=400, detail=f"Failed to fetch or parse OpenAPI schema from: {openapi_url}")

    # Translate the OpenAPI actions into tools
    tools = OpenAPItoMCPTranslator.translate_schema(schema, server_id)
    if not tools:
        raise HTTPException(status_code=400, detail="No valid REST endpoints found in OpenAPI schema to map into tools.")

    server_data = {
        "server_id": server_id,
        "name": name,
        "openapi_url": openapi_url,
        "base_url": base_url,
        "auth_headers": auth_headers,
        "workspace_id": user.workspace_id or "default",
        "registered_at": datetime.utcnow().isoformat(),
        "tools": tools
    }

    _save_server_to_store(server_id, server_data)

    return {
        "status": "success",
        "message": f"Successfully registered server '{server_id}' with {len(tools)} translated tools.",
        "server": {
            "server_id": server_id,
            "name": name,
            "tools_count": len(tools)
        }
    }


@router.get("/mcp/servers")
async def list_mcp_servers(user=Depends(get_current_user)):
    """List all registered dynamic MCP servers for the current workspace."""
    all_servers = get_all_registered_servers()
    ws_id = user.workspace_id or "default"
    # Filter by user workspace ID
    ws_servers = [s for s in all_servers.values() if s.get("workspace_id") == ws_id]
    return ws_servers


@router.delete("/mcp/servers/{server_id}")
async def delete_mcp_server(server_id: str, user=Depends(get_current_user)):
    """Unregister a dynamic MCP server connection."""
    all_servers = get_all_registered_servers()
    server = all_servers.get(server_id)
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")

    if server.get("workspace_id") != (user.workspace_id or "default"):
        raise HTTPException(status_code=403, detail="Not authorized to modify this server connection")

    _delete_server_from_store(server_id)
    return {"status": "success", "message": f"Server '{server_id}' has been successfully unregistered."}


@router.api_route("/proxy/{server_id}/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def mcp_transparent_proxy(server_id: str, path: str, request: Request, user=Depends(get_current_user_optional)):
    """
    Transparent proxy gateway.
    Intercepts the execution, runs zero-trust governance + x402 cost-attribution, 
    injects auth variables, and forwards call to target SaaS.
    """
    if request.method == "OPTIONS":
        # Always allow OPTIONS preflight requests
        return Response(status_code=204)

    all_servers = get_all_registered_servers()
    server = all_servers.get(server_id)
    if not server:
        raise HTTPException(status_code=404, detail=f"Target proxy server '{server_id}' not found.")

    # 1. Zero-Trust & x402 Readiness Verification
    # Run the strict 9-Phase readiness checklist
    runtime = EnhancedMCPAPIRuntime()
    
    # Standard query extraction
    query_params = dict(request.query_params)
    body_bytes = await request.body()
    body_data = {}
    if body_bytes:
        try:
            body_data = json.loads(body_bytes)
        except Exception:
            pass

    # Build the governance payload
    gov_req = {
        "nonce": request.headers.get("X-Veklom-Nonce") or f"nonce_{uuid.uuid4()}",
        "connection_id": f"proxy_{server_id}",
        "agent_id": user.id if user else "anonymous_agent",
        "capability_id": f"call_{server_id}_{path.replace('/', '_')}",
        "payload": body_data,
        "upstream_evidence_hash": request.headers.get("X-Veklom-Evidence-Hash") or "0x" + "0"*64
    }

    gov_response = await runtime.process_request(gov_req)
    if "error" in gov_response:
        # Governance block! Return the exact legal (451) or policy (403) code
        code = int(gov_response["error"].get("code", 403))
        return JSONResponse(status_code=code, content=gov_response)

    # 2. Build the Outbound Request
    target_url = f"{server['base_url'].rstrip('/')}/{path}"
    
    # Inherit and build headers
    headers = {}
    for k, v in request.headers.items():
        if k.lower() not in ("host", "content-length", "authorization", "x-veklom-nonce", "x-veklom-evidence-hash"):
            headers[k] = v

    # Inject configured SaaS authentication headers securely
    for k, v in server.get("auth_headers", {}).items():
        headers[k] = v

    # Forward the call via HTTP client
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                params=query_params,
                content=body_bytes
            )
            
            # Forward the exact response headers and content type
            resp_headers = {}
            for k, v in resp.headers.items():
                if k.lower() not in ("content-encoding", "transfer-encoding", "content-length"):
                    resp_headers[k] = v

            # Inject VNP & x402 proof headers in the response for verification
            resp_headers["X-VNP-Stake-Result"] = "verified"
            resp_headers["X-Veklom-Receipt-ID"] = gov_response.get("evidence_hash") or f"rcpt_{uuid.uuid4()}"

            return Response(
                content=resp.content,
                status_code=resp.status_code,
                headers=resp_headers
            )
    except Exception as e:
        logger.error(f"Failed to forward request to proxy server '{server_id}': {e}")
        raise HTTPException(status_code=502, detail=f"Proxy error: Failed to connect to downstream service. Details: {e}")

# Helper import pattern check
import re
from datetime import datetime
from fastapi.responses import JSONResponse
import uuid
