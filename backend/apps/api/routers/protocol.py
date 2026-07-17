"""
Veklom Protocol Manifest
Serves the self-describing capability manifest and introspection endpoint.

GET  /protocol.json        — machine-readable manifest of all Veklom capabilities
POST /protocol/introspect  — capability discovery query (public, no auth required)
"""
from __future__ import annotations
from typing import Optional, List, Dict, Any
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["Veklom Protocol"])

MANIFEST: Dict[str, Any] = {
    "protocol": "veklom/v1",
    "version": "1.0.0",
    "name": "Veklom Sovereign AI Hub",
    "description": "A self-describing, governed AI execution platform with VNP micro-stakes, GPC pipelines, and OpenAI-compatible inference.",
    "base_url": "https://api.veklom.com",
    "schema": "/openapi.json",
    "introspect": "POST /protocol/introspect",
    "capabilities": {
        "inference": {
            "description": "OpenAI-compatible inference gateway. Preserves system prompts, supports streaming.",
            "endpoints": [
                {"method": "POST", "path": "/v1/chat/completions", "auth": ["bearer", "byos_key"], "description": "Chat completions with full message array passthrough"},
                {"method": "GET", "path": "/v1/models", "auth": ["bearer", "byos_key"], "description": "List available models"}
            ]
        },
        "pipeline": {
            "description": "GPC — Governed Pipeline Compiler. Compile messy intent into deterministic execution graphs.",
            "endpoints": [
                {"method": "POST", "path": "/api/v1/gpc/compile", "auth": ["bearer"], "description": "Compile natural language intent into a GPC pipeline graph"},
                {"method": "POST", "path": "/api/v1/gpc/execute", "auth": ["bearer"], "description": "Execute a compiled GPC pipeline graph"},
                {"method": "GET", "path": "/api/v1/gpc/components", "auth": ["bearer"], "description": "List available GPC node components"}
            ]
        },
        "identity": {
            "description": "PGL IdentityRAG — cross-cluster tenant resolution and identity graph.",
            "endpoints": [
                {"method": "GET", "path": "/api/v1/pgl/registry", "auth": [], "description": "Public PGL registry listing"}
            ]
        },
        "evidence": {
            "description": "Settlement ledger — cryptographic proof of compute execution.",
            "endpoints": [
                {"method": "POST", "path": "/api/v1/evidence/verify", "auth": [], "description": "Verify an evidence record by ID"},
                {"method": "GET", "path": "/api/v1/evidence/export", "auth": ["bearer"], "description": "Export evidence records for a workspace"}
            ]
        },
        "staking": {
            "description": "VNP Micro-Stakes — real-time SLA performance bonds.",
            "endpoints": [
                {"method": "POST", "path": "/api/v1/vnp/stake", "auth": ["bearer"], "description": "Post a VNP stake on a compute SLA"}
            ]
        },
        "auth": {
            "description": "Authentication — JWT login, registration, API key management.",
            "endpoints": [
                {"method": "POST", "path": "/api/v1/auth/login", "auth": [], "description": "Login and receive a JWT"},
                {"method": "POST", "path": "/api/v1/auth/register", "auth": [], "description": "Register a new workspace account"}
            ]
        },
        "workspace": {
            "description": "Workspace management — usage, billing, settings.",
            "endpoints": [
                {"method": "GET", "path": "/api/v1/workspace/overview/live", "auth": ["bearer"], "description": "Live workspace metrics and usage overview"}
            ]
        },
        "agents": {
            "description": "Autonomous agent management and execution.",
            "endpoints": [
                {"method": "GET", "path": "/api/v1/agents", "auth": ["bearer"], "description": "List all agents in the workspace"}
            ]
        },
        "payments": {
            "description": "x402 payment protocol — pay-per-request AI compute.",
            "endpoints": [
                {"method": "POST", "path": "/api/v1/x402", "auth": [], "description": "Initiate an x402 compute payment"}
            ]
        }
    },
    "_links": {
        "schema": {"href": "/openapi.json", "method": "GET"},
        "health": {"href": "/health", "method": "GET"},
        "introspect": {"href": "/protocol/introspect", "method": "POST"},
        "models": {"href": "/v1/models", "method": "GET"},
        "inference": {"href": "/v1/chat/completions", "method": "POST"}
    }
}


class IntrospectRequest(BaseModel):
    query: str
    capability_group: Optional[str] = None


@router.get("/protocol.json", include_in_schema=True)
async def get_protocol_manifest():
    """Veklom Protocol Manifest — self-describing capability registry."""
    return MANIFEST


@router.post("/protocol/introspect", include_in_schema=True)
async def introspect_capabilities(body: IntrospectRequest):
    """
    Capability discovery endpoint.
    Accepts a natural language or keyword query and returns matching capabilities.
    Public — no auth required. Used by UACP V3, MCP clients, and GPC node executor.
    """
    query = body.query.lower()
    group_filter = (body.capability_group or "").lower()

    results: List[Dict[str, Any]] = []
    for group_name, group_data in MANIFEST["capabilities"].items():
        if group_filter and group_filter not in group_name:
            continue
        desc = group_data.get("description", "").lower()
        if query in group_name or query in desc or any(query in ep.get("description", "").lower() for ep in group_data.get("endpoints", [])):
            results.append({
                "capability_group": group_name,
                "description": group_data["description"],
                "endpoints": group_data["endpoints"],
                "match_score": 1.0 if query in group_name else 0.7
            })

    return {
        "query": body.query,
        "protocol_version": MANIFEST["protocol"],
        "matches": sorted(results, key=lambda x: x["match_score"], reverse=True),
        "total": len(results),
        "_links": {
            "manifest": {"href": "/protocol.json", "method": "GET"},
            "schema": {"href": "/openapi.json", "method": "GET"}
        }
    }
