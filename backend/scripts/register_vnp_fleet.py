import asyncio
import uuid
import sys
import os

# Add the project root to the python path so imports work
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from backend.core.database.database import async_session
from backend.db.models.agent import AgentIdentity, Account, AgentUser
from backend.services.pgl_client import PGLClient

async def register_vnp_fleet(fleet_size: int = 120, workspace_id: str = "vnp-founder-workspace"):
    """
    Registers a fleet of VNP prober agents into the Provenance Governance Ledger (PGL).
    Ensures that each Ollama agent running locally has a verifiable, auditable identity.
    """
    print(f"Starting registration of {fleet_size} VNP Agents into PGL...")
    
    async with async_session() as db:
        pgl = PGLClient(db)
        
        # We need a creator PGL ID to anchor the lineage. 
        # Using a deterministic system ID for the VNP founder/deployer.
        creator_pgl_id = f"sys_founder_{workspace_id[:8]}"
        
        registered_count = 0
        
        for i in range(1, fleet_size + 1):
            agent_id = f"vnp-prober-node-{i:03d}"
            agent_name = f"VNP Routing Prober {i:03d}"
            
            # 1. Check if the agent already exists to make this script idempotent
            existing = (await db.execute(
                select(AgentIdentity).where(AgentIdentity.id == agent_id)
            )).scalar_one_or_none()
            
            if existing:
                print(f"[-] Agent {agent_id} already registered. Skipping.")
                continue
                
            # 2. Create the AgentIdentity record
            identity = AgentIdentity(
                id=agent_id,
                tenant_id=workspace_id,
                name=agent_name,
                created_by_pgl_id=creator_pgl_id,
                description="Autonomous VNP data-plane routing and telemetry agent running on local Ollama enclave.",
                metadata_json={
                    "vnp_role": "prober_node",
                    "engine": "ollama",
                    "region": "local-enclave"
                }
            )
            db.add(identity)
            
            # 3. Anchor the agent's creation into the Immutable PGL Ledger
            # This ensures that all actions taken by this agent have a verifiable origin.
            await pgl.record_event(
                workspace_id=workspace_id,
                actor_id=creator_pgl_id,
                certificate_id=None,
                event_type="vnp_agent_registration",
                payload={
                    "agent_id": agent_id,
                    "agent_name": agent_name,
                    "role": "vnp-prober-node",
                    "engine": "ollama",
                    "timestamp": asyncio.get_event_loop().time()
                }
            )
            
            registered_count += 1
            if i % 10 == 0:
                print(f"    ...Registered {i}/{fleet_size} agents")
                await db.commit() # batch commit
                
        # Final commit for any remainders
        await db.commit()
        
        print(f"\n[+] Successfully registered {registered_count} new VNP agents into PGL.")
        print(f"[+] All agents anchored to workspace: {workspace_id}")

if __name__ == "__main__":
    asyncio.run(register_vnp_fleet())
