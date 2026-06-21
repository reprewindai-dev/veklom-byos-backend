from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
import json
import os
from pathlib import Path

# We don't strictly require authentication here since the PGL registry
# is public system state, but we could add Depends(get_current_user) if needed.
# For the terminal handshake, we'll keep it open but rate limited.

router = APIRouter(prefix="/pgl", tags=["PGL Registry"])

def get_pgl_registry_path() -> Path:
    # Path to the actual agent army registry in the backend
    base_dir = Path(os.getcwd())
    registry_path = base_dir / "agents" / "veklom-agents" / "pgl_registry.json"
    
    # Fallback for different execution contexts
    if not registry_path.exists():
        # Try relative to this file
        current_dir = Path(__file__).parent
        registry_path = current_dir.parent.parent.parent.parent / "agents" / "veklom-agents" / "pgl_registry.json"
        
    return registry_path

@router.get("/registry", response_model=List[Dict[str, Any]])
async def get_pgl_registry():
    """
    Serve the authoritative PGL registry to external terminals and clients.
    This acts as the deterministic source of truth for agent identities.
    """
    registry_path = get_pgl_registry_path()
    
    if not registry_path.exists():
        raise HTTPException(
            status_code=500, 
            detail=f"PGL Registry not found on backend system. Looked in {registry_path}"
        )
        
    try:
        with open(registry_path, "r", encoding="utf-8") as f:
            registry_data = json.load(f)
            return registry_data
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to parse PGL registry: {str(e)}"
        )
