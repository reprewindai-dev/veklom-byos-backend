from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends
from backend.core.security.auth import get_current_user

router = APIRouter(tags=["discovery"])

@router.get("/listings", response_model=List[Dict[str, Any]])
async def get_discovery_agents(current_user: dict = Depends(get_current_user)):
    # Returns dummy/static discovery listings until fully integrated
    return [
        {
            "id": "ls_co2router",
            "name": "CO2 Routing Agent",
            "title": "CO2 Routing Agent",
            "slug": "co2-routing",
            "visibility": "public",
            "status": "active",
            "state": "published",
            "datasheet_hash": "ds_a8f93be81a",
        },
        {
            "id": "ls_vault",
            "name": "Governance Vault",
            "title": "Governance Vault",
            "slug": "governance-vault",
            "visibility": "public",
            "status": "active",
            "state": "published",
            "datasheet_hash": "ds_c7129ff28e",
        }
    ]

@router.get("/installed", response_model=List[Dict[str, Any]])
async def get_installed_agents(current_user: dict = Depends(get_current_user)):
    # Returns dummy/static installed assets for this workspace
    ws_id = current_user.workspace_id if current_user and hasattr(current_user, 'workspace_id') else "ws_unknown"
    return [
        {
            "id": "inst_123",
            "name": "CO2 Routing Agent (Installed)",
            "listing_name": "CO2 Routing Agent",
            "asset_id": "ls_co2router",
            "workspace_id": ws_id,
            "tenant_id": ws_id,
            "provider": "anthropic",
            "provider_id": "claude-3-5-sonnet",
            "model_id": "claude-3-5-sonnet-20240620"
        }
    ]

@router.get("/state")
async def get_discovery_state(current_user: dict = Depends(get_current_user)):
    return {
        "source": {
            "discovery_app": "https://discovery.veklom.com",
            "byos": "https://api.veklom.com"
        },
        "proof": {
            "state": "verified",
            "reason": "Discovery node connected successfully",
            "probes": [
                {
                    "route": "https://discovery.veklom.com",
                    "state": "verified",
                    "status": 200,
                    "detail": "Live discovery origin"
                }
            ]
        },
        "registryRows": 2,
        "paidSearch": None
    }
