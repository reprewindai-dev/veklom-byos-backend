"""PGL Client — connects to GnomLedger (the real PGL system).

This client connects to GnomLedger for agent registration, certificates,
and ledger events. GnomLedger is the source of truth for PGL certificates
and agent birth certificates.
"""

from __future__ import annotations

import httpx
from typing import Any, Dict, Optional
from backend.core.config.settings import settings


class PGLClient:
    """Client for connecting to GnomLedger (real PGL system)."""
    
    def __init__(self):
        # Ensure we point to the api/v1 prefix of GnomLedger
        url = settings.GNOMLEDGER_URL or "http://localhost:8001"
        if not url.endswith("/api/v1"):
            url = url.rstrip("/") + "/api/v1"
        self.base_url = url
        self.timeout = 30.0
        self.headers = {
            "X-API-Key": settings.GNOMLEDGER_API_KEY or "",
            "Content-Type": "application/json"
        }
    
    async def register_agent(
        self,
        *,
        agent_id: str,
        name: str,
        creator: str,
        jurisdiction: str,
        declared_purpose: str,
        genome_payload: Dict[str, Any],
        parent_agent_ids: list[str] | None = None,
    ) -> Dict[str, Any]:
        """Register an agent with GnomLedger and get birth certificate."""
        
        # Map to GnomLedger's AgentCreateRequest schema
        payload = {
            "agent_name": name,
            "creator": creator,
            "jurisdiction": jurisdiction,
            "genome": genome_payload,
            "parent_agent_ids": parent_agent_ids or [],
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/agents",
                json=payload,
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
    
    async def list_agents(
        self,
        limit: int = 100,
        cursor: int | None = None,
    ) -> list[Dict[str, Any]]:
        """List all agents from GnomLedger."""
        
        params = {"limit": limit}
        if cursor:
            params["cursor"] = cursor
            
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.base_url}/agents",
                params=params,
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
    
    async def get_agent(
        self,
        agent_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get agent details from GnomLedger."""
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.base_url}/agents/{agent_id}",
                headers=self.headers
            )
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()
    
    async def get_agent_certificate(
        self,
        agent_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get agent certificate from GnomLedger."""
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.base_url}/agents/{agent_id}/certificate",
                headers=self.headers
            )
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()
    
    async def create_ledger_event(
        self,
        *,
        agent_id: str,
        event_type: str,
        actor: str = "veklom-system",
        summary: str = "Agent execution event",
        details: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create a ledger event in GnomLedger."""
        
        # Map to GnomLedger's LedgerEventCreate schema
        payload = {
            "agent_id": agent_id,
            "event_type": event_type,
            "actor": actor,
            "summary": summary,
            "details": details,
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/ledger/events",
                json=payload,
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
    
    async def get_agent_history(
        self,
        agent_id: str,
        limit: int = 200,
    ) -> list[Dict[str, Any]]:
        """Get agent ledger history from GnomLedger."""
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.base_url}/ledger/agents/{agent_id}",
                params={"limit": limit},
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
    
    async def verify_agent_chain(
        self,
        agent_id: str,
    ) -> Dict[str, Any]:
        """Verify agent chain in GnomLedger."""
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.base_url}/ledger/agents/{agent_id}/verify",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
