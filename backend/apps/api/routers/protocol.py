"""BYOS protocol discovery endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["Protocol"])

MANIFEST: dict[str, Any] = {
    "service": "byos",
    "repo": "reprewindai-dev/veklom-byos-backend",
    "role": "sovereign backend / control-plane core",
    "version": "1.0.0",
    "base_url": "https://api.veklom.com",
    "health": "/health",
    "dependencies": "/health/dependencies",
    "auth_mode": "route-specific (bearer JWT, API key, or x402)",
    "status": "ok",
    "capabilities": [
        "governed_execution",
        "build_evidence_packs",
        "compile_governed_plans",
        "ingest_edge_webhooks",
    ],
    "capability_endpoints": {
        "governed_execution": "POST /api/v1/capi/execute",
        "build_evidence_packs": "POST /api/v1/evidence/build",
        "compile_governed_plans": "POST /api/v1/gpc/compile",
        "ingest_edge_webhooks": "POST /api/v1/edge/input/webhook",
    },
    "links": {
        "byos": "https://api.veklom.com/protocol.json",
        "capi": "https://capi.veklom.com/protocol.json",
        "cappo": "https://cappo.veklom.com/protocol.json",
        "pgl": "https://pgl.veklom.com/protocol.json",
    },
}


class IntrospectQuery(BaseModel):
    query: str


@router.get("/protocol.json", include_in_schema=False)
async def get_protocol_manifest() -> dict[str, Any]:
    return MANIFEST


@router.post("/protocol/introspect", include_in_schema=False)
async def introspect_capabilities(body: IntrospectQuery) -> dict[str, Any]:
    query = body.query.lower()
    capabilities = MANIFEST["capabilities"]
    matches = [capability for capability in capabilities if query == "*" or query in capability]
    return {
        "query": body.query,
        "matches": matches,
        "total": len(matches),
        "auth_mode": MANIFEST["auth_mode"],
        "links": MANIFEST["links"],
    }
