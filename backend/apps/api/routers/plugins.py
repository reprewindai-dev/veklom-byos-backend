"""Plugin management endpoints."""

from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from backend.core.database.database import get_db
from backend.core.security.auth import get_current_user
from backend.core.plugins.manager import plugin_manager
from backend.db.models.plugin import WorkspacePlugin

router = APIRouter(tags=["Plugins"])


class PluginResponse(BaseModel):
    id: str
    name: str
    version: str
    description: str
    enabled: bool
    workspace_id: str | None


class PluginConfigUpdate(BaseModel):
    config: Dict[str, Any]


@router.get("/v1/plugins", response_model=List[PluginResponse])
async def list_plugins(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """List all available plugins and their enablement state for the current workspace."""
    workspace_id = user.default_workspace_id
    if not workspace_id:
        return []

    # Get globally discovered plugins
    discovered = plugin_manager.list_discovered_plugins()
    
    # Get workspace-specific overrides/states
    result = await db.execute(
        select(WorkspacePlugin).where(WorkspacePlugin.workspace_id == workspace_id)
    )
    workspace_states = {wp.plugin_id: wp for wp in result.scalars().all()}
    
    response = []
    for p_id, meta in discovered.items():
        state = workspace_states.get(p_id)
        response.append(
            PluginResponse(
                id=p_id,
                name=meta["name"],
                version=meta["version"],
                description=meta["description"],
                enabled=state.enabled if state else False,
                workspace_id=workspace_id
            )
        )
    return response


@router.post("/v1/plugins/{plugin_id}/enable")
async def enable_plugin(plugin_id: str, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Enable a specific plugin for the workspace."""
    workspace_id = user.default_workspace_id
    if not workspace_id:
        raise HTTPException(status_code=400, detail="No active workspace.")
        
    discovered = plugin_manager.list_discovered_plugins()
    if plugin_id not in discovered:
        raise HTTPException(status_code=404, detail="Plugin not found.")

    result = await db.execute(
        select(WorkspacePlugin).where(
            WorkspacePlugin.workspace_id == workspace_id,
            WorkspacePlugin.plugin_id == plugin_id
        )
    )
    wp = result.scalar_one_or_none()
    
    if wp:
        wp.enabled = True
    else:
        wp = WorkspacePlugin(workspace_id=workspace_id, plugin_id=plugin_id, enabled=True)
        db.add(wp)
        
    await db.commit()
    return {"status": "success", "enabled": True}


@router.post("/v1/plugins/{plugin_id}/disable")
async def disable_plugin(plugin_id: str, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Disable a specific plugin for the workspace."""
    workspace_id = user.default_workspace_id
    if not workspace_id:
        raise HTTPException(status_code=400, detail="No active workspace.")

    result = await db.execute(
        select(WorkspacePlugin).where(
            WorkspacePlugin.workspace_id == workspace_id,
            WorkspacePlugin.plugin_id == plugin_id
        )
    )
    wp = result.scalar_one_or_none()
    
    if wp:
        wp.enabled = False
        await db.commit()
        
    return {"status": "success", "enabled": False}


@router.post("/v1/plugins/{plugin_id}/config")
async def configure_plugin(plugin_id: str, payload: PluginConfigUpdate, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Set the workspace-scoped configuration for a plugin."""
    workspace_id = user.default_workspace_id
    if not workspace_id:
        raise HTTPException(status_code=400, detail="No active workspace.")
        
    # TODO: Encrypt config before saving
    # For now, storing as stringified json or raw dict depending on DB schema
    import json
    
    result = await db.execute(
        select(WorkspacePlugin).where(
            WorkspacePlugin.workspace_id == workspace_id,
            WorkspacePlugin.plugin_id == plugin_id
        )
    )
    wp = result.scalar_one_or_none()
    
    if wp:
        wp.encrypted_config = json.dumps(payload.config)
    else:
        wp = WorkspacePlugin(
            workspace_id=workspace_id, 
            plugin_id=plugin_id, 
            enabled=False,
            encrypted_config=json.dumps(payload.config)
        )
        db.add(wp)
        
    await db.commit()
    return {"status": "success"}


@router.get("/v1/plugins/{plugin_id}/health")
async def plugin_health(plugin_id: str, user=Depends(get_current_user)):
    """Check the operational health of a loaded plugin."""
    plugin = plugin_manager.get_plugin(plugin_id)
    if not plugin:
        return {"healthy": False, "detail": "Plugin not initialized or not found."}
        
    try:
        is_healthy = await plugin.health_check()
        return {"healthy": is_healthy}
    except Exception as e:
        return {"healthy": False, "detail": str(e)}
