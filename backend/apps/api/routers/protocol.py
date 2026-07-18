"""
Veklom Protocol Manifest
Serves the self-describing capability manifest and introspection endpoint.
"""
from typing import Dict, Any
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["Veklom Protocol"])

MANIFEST: Dict[str, Any] = {
    "service": "veklom-byos-backend",
    "repo": "reprewindai-dev/veklom-byos-backend",
    "role": "sovereign-control-plane",
    "version": "2026.07",
    "base_url": "https://api.veklom.com",
    "health": "/health",
    "dependencies": "/health/dependencies",
    "auth_mode": "bearer",
    "status": "ok",
    "capabilities": [
        "auth",
        "workspace",
        "vnp",
        "x402",
        "gpc",
        "pgl-proxy",
        "inference"
    ],
    "links": {
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
    # Semantic/keyword capability discovery
    q = query.query.lower()
    matches = [cap for cap in MANIFEST["capabilities"] if q in cap.lower()]
    return {"capabilities": matches}
