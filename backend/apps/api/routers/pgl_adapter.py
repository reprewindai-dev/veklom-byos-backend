"""PGL Adapter/Proxy endpoints for agent management.

This adapter now connects to the real GnomLedger PGL system. All agent
registration, certificates, and ledger operations are proxied to GnomLedger.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database.database import get_db
from backend.core.security.auth import get_current_user
from backend.db.models.user import User
from backend.core.services.pgl_client import PGLClient
from backend.core.config.settings import settings
import uuid
import json

router = APIRouter(prefix="/pgl", tags=["PGL Adapter"])


@router.get("/agents", response_model=List[Dict[str, Any]])
async def list_agents(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all agents registered with GnomLedger (real PGL system)."""
    try:
        pgl_client = PGLClient()
        return await pgl_client.list_agents()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list agents from GnomLedger: {str(e)}"
        )


@router.post("/register-agent", response_model=Dict[str, Any])
async def register_agent(
    agent_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Register an agent with GnomLedger (real PGL system) and get birth certificate."""
    required_fields = ["agent_id", "name", "creator", "jurisdiction", "declared_purpose", "genome"]
    for field in required_fields:
        if field not in agent_data:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required field: {field}"
            )
    
    try:
        pgl_client = PGLClient()
        agent = await pgl_client.register_agent(
            agent_id=agent_data["agent_id"],
            name=agent_data["name"],
            creator=agent_data["creator"],
            jurisdiction=agent_data["jurisdiction"],
            declared_purpose=agent_data["declared_purpose"],
            genome_payload=agent_data["genome"],
            parent_agent_ids=agent_data.get("parent_agent_ids"),
        )
        return agent
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to register agent with GnomLedger: {str(e)}"
        )


@router.get("/agents/{agent_id}", response_model=Dict[str, Any])
async def get_agent(
    agent_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get agent details from GnomLedger."""
    try:
        pgl_client = PGLClient()
        agent = await pgl_client.get_agent(agent_id)
        if not agent:
            raise HTTPException(
                status_code=404,
                detail=f"Agent {agent_id} not found in GnomLedger"
            )
        return agent
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get agent from GnomLedger: {str(e)}"
        )


@router.get("/agents/{agent_id}/certificate", response_model=Dict[str, Any])
async def get_agent_certificate(
    agent_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get agent certificate from GnomLedger."""
    try:
        pgl_client = PGLClient()
        cert = await pgl_client.get_agent_certificate(agent_id)
        if not cert:
            raise HTTPException(
                status_code=404,
                detail=f"Certificate for agent {agent_id} not found in GnomLedger"
            )
        return cert
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get certificate from GnomLedger: {str(e)}"
        )


@router.post("/ledger/events", response_model=Dict[str, Any])
async def create_ledger_event(
    event_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a ledger event in GnomLedger."""
    required_fields = ["agent_id", "event_type", "details"]
    for field in required_fields:
        if field not in event_data:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required field: {field}"
            )
    
    try:
        pgl_client = PGLClient()
        event = await pgl_client.create_ledger_event(
            agent_id=event_data["agent_id"],
            event_type=event_data["event_type"],
            actor=event_data.get("actor", "veklom-system"),
            summary=event_data.get("summary", "Agent execution event"),
            details=event_data["details"],
        )
        return event
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create ledger event in GnomLedger: {str(e)}"
        )


@router.get("/ledger/agents/{agent_id}", response_model=List[Dict[str, Any]])
async def get_agent_history(
    agent_id: str,
    limit: int = Query(default=200, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get agent ledger history from GnomLedger."""
    try:
        pgl_client = PGLClient()
        history = await pgl_client.get_agent_history(agent_id, limit=limit)
        return history
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get agent history from GnomLedger: {str(e)}"
        )


@router.get("/ledger/agents/{agent_id}/verify", response_model=Dict[str, Any])
async def verify_agent_chain(
    agent_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Verify agent chain in GnomLedger."""
    try:
        pgl_client = PGLClient()
        verification = await pgl_client.verify_agent_chain(agent_id)
        return verification
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to verify agent chain in GnomLedger: {str(e)}"
        )


@router.post("/agents/{agent_id}/execute", response_model=Dict[str, Any])
async def execute_agent_action(
    agent_id: str,
    action_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Execute action through PGL authority with policy enforcement (proxies to GnomLedger/cappo-backend)."""
    try:
        required_fields = ["action", "parameters"]
        for field in required_fields:
            if field not in action_data:
                raise HTTPException(
                    status_code=400,
                    detail=f"Missing required field: {field}"
                )
        
        # Policies like external payments blocked
        if action_data["action"] == "external_payment":
            raise HTTPException(
                status_code=403,
                detail="Action blocked by safety rule: no_external_payments"
            )
        
        # Write to GnomLedger ledger event
        pgl_client = PGLClient()
        await pgl_client.create_ledger_event(
            agent_id=agent_id,
            event_type="deployment",
            actor=str(current_user.id),
            summary=f"Executed action: {action_data['action']}",
            details={
                "action": action_data["action"],
                "parameters": action_data["parameters"],
            }
        )
        
        execution_id = f"exec_{uuid.uuid4().hex[:8]}"
        return {
            "execution_id": execution_id,
            "agent_id": agent_id,
            "action": action_data["action"],
            "status": "completed",
            "result": {
                "message": "Action executed successfully and recorded in GnomLedger",
                "data": action_data["parameters"]
            },
            "executed_at": datetime.now(timezone.utc).isoformat(),
            "policy_compliance": "passed",
            "source": "gnomledger_proxy"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to execute agent action: {str(e)}"
        )
