"""
Veklom Protocol Manifest
Serves the self-describing capability manifest and introspection endpoint.
"""
from typing import Dict, Any
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["Veklom Protocol"])

MANIFEST: Dict[str, Any] = {
    "protocol": "veklom/v1",
    "version": "1.0.0",
    "name": "Veklom Sovereign AI Hub",
    "description": "A self-describing, governed AI execution platform",
    "base_url": "https://api.veklom.com",
    "health": "/health",
    "capabilities": [
        {
            "name": "Inference API",
            "endpoint": "POST /api/v1/openai/v1/chat/completions",
            "description": "Governed OpenAI-compatible chat completions.",
            "accepts": ["Bearer JWT"],
            "models": ["qwen2.5-coder:1.5b", "gpt-4o-mini"]
        },
        {
            "name": "Pipeline Compile",
            "endpoint": "POST /api/v1/gpc/compile",
            "description": "Compile a governed pipeline graph into executable bytecode.",
            "accepts": ["Bearer JWT"]
        },
        {
            "name": "Pipeline Execute",
            "endpoint": "POST /api/v1/gpc/execute",
            "description": "Execute a compiled pipeline node or graph.",
            "accepts": ["Bearer JWT"]
        },
        {
            "name": "PGL Registry",
            "endpoint": "GET /api/v1/pgl/registry",
            "description": "IdentityRAG cross-cluster tenant resolution mapping.",
            "accepts": ["Bearer JWT"]
        },
        {
            "name": "Evidence Verify",
            "endpoint": "POST /api/v1/evidence/verify",
            "description": "Verify cryptographic proof of an execution run.",
            "accepts": ["Bearer JWT"]
        },
        {
            "name": "VNP Stake",
            "endpoint": "POST /api/v1/vnp/stake",
            "description": "Real-time SLA performance bonds.",
            "accepts": ["Bearer JWT"]
        },
        {
            "name": "Auth Register",
            "endpoint": "POST /api/v1/auth/register",
            "description": "Register a new tenant or user.",
            "accepts": []
        },
        {
            "name": "Auth Login",
            "endpoint": "POST /api/v1/auth/login",
            "description": "Authenticate a user.",
            "accepts": []
        },
        {
            "name": "Workspace Overview",
            "endpoint": "GET /api/v1/workspace/overview/live",
            "description": "Retrieve live workspace status.",
            "accepts": ["Bearer JWT"]
        },
        {
            "name": "Agents Registry",
            "endpoint": "GET /api/v1/agents",
            "description": "List governed agents.",
            "accepts": ["Bearer JWT"]
        },
        {
            "name": "x402 Payments",
            "endpoint": "POST /api/v1/x402",
            "description": "Settle proof of paid compute.",
            "accepts": ["Bearer JWT"]
        }
    ],
    "links": {
        "self": "https://api.veklom.com/protocol.json",
        "cappo": "https://capi.veklom.com/protocol.json",
        "ledger": "https://ledger.veklom.com/protocol.json",
        "interlink": "https://interlink.veklom.com/protocol.json"
    }
}

class IntrospectQuery(BaseModel):
    query: str

@router.get("/protocol.json")
async def get_protocol_manifest():
    return MANIFEST

@router.post("/protocol/introspect")
async def introspect_protocol(query: IntrospectQuery):
    q = query.query.lower()
    matches = [
        cap for cap in MANIFEST["capabilities"]
        if q in cap["name"].lower() or q in cap.get("description", "").lower() or q in cap["endpoint"].lower()
    ]
    return {"capabilities": matches}
