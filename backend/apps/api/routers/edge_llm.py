import json
import logging
from typing import Any, Dict, Optional
import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from backend.core.security.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/edge-llm", tags=["Edge LLM Tunnels"])

class TunnelRequest(BaseModel):
    tunnel_url: str = Field(..., description="The Ngrok or Cloudflare tunnel URL pointing to the edge Ollama/vLLM instance.")
    model: str = Field(default="qwen2.5:3b", description="The local model to run.")
    prompt: str = Field(..., description="The user instruction or prompt.")
    system_prompt: Optional[str] = Field(None, description="Optional system instructions.")
    structured_schema: Optional[Dict[str, Any]] = Field(None, description="A JSON schema that the output MUST adhere to.")

class TunnelResponse(BaseModel):
    status: str
    tunnel_url: str
    model: str
    response: Any
    latency_ms: float

@router.post("/generate", response_model=TunnelResponse)
async def proxy_to_edge_tunnel(
    body: TunnelRequest,
    user=Depends(get_current_user)
):
    """
    Proxies a generation request to a Sovereign Edge Node running a local LLM (e.g., via Ngrok).
    Enforces structured output if a JSON schema is provided.
    """
    import time
    start = time.time()
    
    # Clean tunnel URL
    base_url = body.tunnel_url.rstrip("/")
    if not base_url.startswith("http"):
        base_url = f"https://{base_url}"
        
    # Build Ollama-compatible payload
    payload = {
        "model": body.model,
        "prompt": body.prompt,
        "stream": False
    }
    
    if body.system_prompt:
        payload["system"] = body.system_prompt
        
    if body.structured_schema:
        # Enforce JSON output matching the schema (Ollama native format)
        payload["format"] = body.structured_schema
        
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(f"{base_url}/api/generate", json=payload)
            
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail=f"Edge node returned error: {resp.text}")
            
        data = resp.json()
        raw_response = data.get("response", "")
        
        # If schema was enforced, parse it as JSON
        final_response = raw_response
        if body.structured_schema:
            try:
                final_response = json.loads(raw_response)
            except json.JSONDecodeError:
                logger.warning(f"Edge node failed to return valid JSON: {raw_response}")
                # Fallback to string if parsing fails
                final_response = raw_response
                
        latency = round((time.time() - start) * 1000, 2)
        
        return TunnelResponse(
            status="completed",
            tunnel_url=base_url,
            model=body.model,
            response=final_response,
            latency_ms=latency
        )
        
    except httpx.RequestError as e:
        logger.error(f"Failed to connect to edge tunnel {base_url}: {e}")
        raise HTTPException(status_code=504, detail="Failed to reach the Edge LLM Tunnel. Ensure the tunnel is online.")
