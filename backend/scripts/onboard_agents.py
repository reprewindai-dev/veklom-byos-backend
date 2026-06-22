import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import uuid
import hashlib
import json
from datetime import datetime, timezone
from sqlalchemy import select

from backend.core.database.database import async_session
from backend.db.models.agent import Agent
from backend.db.models.pgl import PGLCertificate, PGLLedgerEvent, PGLIdentity
from backend.db.models.lineage import BirthCertificate
from backend.db.models.authority import AuthorityBundle, AuthorityRun

def _canonical_hash(obj: dict) -> str:
    canonical = json.dumps(obj, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()

async def onboard_agents():
    async with async_session() as db:
        print("Starting Agent Onboarding Process...")
        
        # Get all agents
        result = await db.execute(select(Agent))
        agents = result.scalars().all()
        
        if not agents:
            print("No agents found in database.")
            return

        for agent in agents:
            print(f"\nProcessing Agent: {agent.name} (ID: {agent.agent_id})")
            
            # Check if birth certificate already exists
            bc_result = await db.execute(
                select(BirthCertificate).where(BirthCertificate.agent_id == agent.id)
            )
            if bc_result.scalar_one_or_none():
                print(f"Agent {agent.name} is already onboarded. Skipping.")
                continue

            # Generate IDs and Hashes
            workspace_id = "default_workspace"
            actor_id = agent.creator or "system"
            certificate_id = f"ubc_{uuid.uuid4().hex[:16]}"
            
            genome_payload = {
                "agent_name": agent.name,
                "agent_type": "autonomous",
                "capabilities": agent.capabilities or [],
                "safety_rules": ["no_secrets"],
                "tools": ["governance", "policy-check"],
                "permissions": ["read", "write"],
                "workspace_id": workspace_id,
                "version": "1.0.0",
            }
            genome_hash = _canonical_hash(genome_payload)
            
            constitution_data = {
                "tools": ["governance", "policy-check"],
                "permissions": ["read", "write"],
                "safety_rules": ["no_secrets"],
            }
            constitution_hash = _canonical_hash(constitution_data)

            # 1. Create PGLCertificate
            pgl_cert = PGLCertificate(
                certificate_id=certificate_id,
                kind="birth",
                workspace_id=workspace_id,
                actor_id=actor_id,
                genome_hash=genome_hash,
                constitution_hash=constitution_hash,
                status="active",
                created_at=datetime.now(timezone.utc)
            )
            db.add(pgl_cert)

            # 2. Create BirthCertificate (for Authority Context)
            birth_cert = BirthCertificate(
                agent_id=agent.id,
                certificate_id=certificate_id,
                genome_hash=genome_hash,
                document_uri=f"pgl://{workspace_id}/{certificate_id}",
                parent_agent_ids=[],
                issued_at=datetime.now(timezone.utc)
            )
            db.add(birth_cert)

            # 3. Create initial PGLLedgerEvent
            chain_input = json.dumps({"genome": genome_hash, "constitution": constitution_hash}, sort_keys=True, separators=(",", ":"))
            chain_input += "GENESIS"
            event_hash = hashlib.sha256(chain_input.encode()).hexdigest()

            ledger_event = PGLLedgerEvent(
                workspace_id=workspace_id,
                actor_id=actor_id,
                certificate_id=certificate_id,
                event_type="agent_registered",
                payload={"genome_hash": genome_hash},
                prev_event_hash=None,
                event_hash=event_hash,
                created_at=datetime.now(timezone.utc)
            )
            db.add(ledger_event)
            
            # 4. Create AuthorityBundle
            bundle_id = f"bundle_{uuid.uuid4().hex[:16]}"
            authority_bundle = AuthorityBundle(
                id=bundle_id,
                name=f"{agent.name} Standard Authority",
                version="1.0.0",
                workspace_id=workspace_id,
                creator_id=actor_id,
                risk_level="low",
                tool_permissions={"*": {"allowed": True}},
                workspace_restrictions={},
                time_restrictions={},
                description="Default authority bundle generated during onboarding",
                tags=["default", "auto-generated"],
                is_active=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            db.add(authority_bundle)
            
            # 5. Create active AuthorityRun
            run_id = f"run_{uuid.uuid4().hex[:16]}"
            authority_run = AuthorityRun(
                id=run_id,
                authority_bundle_id=bundle_id,
                agent_id=agent.agent_id,
                workspace_id=workspace_id,
                executor_id=actor_id,
                status="active",
                start_time=datetime.now(timezone.utc),
                total_actions=0,
                approved_actions=0,
                denied_actions=0,
                violation_count=0,
                decisions=[],
                violations=[],
                approvals=[],
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            db.add(authority_run)

            print(f"Successfully onboarded {agent.name} with PGL Certificate {certificate_id}")
            
        await db.commit()
        print("\nAll agents onboarded successfully! PGL Profiles and Authority Contexts are now available.")

if __name__ == "__main__":
    asyncio.run(onboard_agents())
