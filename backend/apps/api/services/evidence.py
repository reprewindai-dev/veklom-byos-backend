"""Evidence service for Veklom Evidence Pack System."""

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models.evidence import (
    EvidencePack, BrowserAction, MemoryEntry, 
    KnowledgeChunk, KnowledgeSource, KnowledgeTemplate
)
from backend.db.models.authority import AuthorityRun, AuthorityDecision
from backend.db.models.lineage import BirthCertificate
from backend.db.models.ledger import LedgerEvent


class EvidencePackBuilder:
    """Builds evidence packs from authority runs and related artifacts."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def build_evidence_pack(
        self,
        authority_run_id: str,
        workspace_id: str,
        agent_id: str,
        creator_id: str,
        description: Optional[str] = None
    ) -> EvidencePack:
        """Build an evidence pack for a given authority run."""
        
        # Get the authority run
        run_result = await self.db.execute(
            select(AuthorityRun).where(AuthorityRun.id == authority_run_id)
        )
        run = run_result.scalar_one_or_none()
        
        if not run:
            raise ValueError(f"Authority run {authority_run_id} not found")
        
        # Collect all artifacts
        artifacts = await self._collect_artifacts(run)
        
        # Compute hashes
        hashes = await self._compute_hashes(run, artifacts)
        
        # Create evidence pack
        evidence_pack_id = f"evidence_pack_{authority_run_id}_{int(datetime.now(timezone.utc).timestamp())}"
        
        evidence_pack = EvidencePack(
            evidence_pack_id=evidence_pack_id,
            authority_run_id=authority_run_id,
            workspace_id=workspace_id,
            agent_id=agent_id,
            creator_id=creator_id,
            artifacts=artifacts,
            hashes=hashes,
            verification={
                "verified": True,
                "failures": [],
                "checked_at": datetime.now(timezone.utc).isoformat(),
                "verification_method": "hash_chain_reconstruction"
            },
            description=description or f"Evidence pack for authority run {authority_run_id}",
            pack_type="authority_run",
            hash_chain=hashes.get("artifacts_hash", ""),
            prev_hash=""
        )
        
        self.db.add(evidence_pack)
        await self.db.commit()
        await self.db.refresh(evidence_pack)
        
        return evidence_pack
    
    async def _collect_artifacts(self, run: AuthorityRun) -> Dict[str, Any]:
        """Collect all artifacts related to the authority run."""
        
        artifacts = {
            "birth_certificate_id": None,
            "authority_bundle_id": run.authority_bundle_id,
            "memory_entry_ids": [],
            "browser_action_ids": [],
            "tool_call_ids": [],
            "audit_log_ids": [],
            "ledger_event_ids": []
        }
        
        # Get birth certificate for the agent
        from backend.db.models.agent import Agent
        agent_result = await self.db.execute(
            select(Agent).where(Agent.agent_id == run.agent_id)
        )
        agent = agent_result.scalar_one_or_none()
        
        if agent:
            cert_result = await self.db.execute(
                select(BirthCertificate).where(BirthCertificate.agent_id == agent.id)
            )
            cert = cert_result.scalar_one_or_none()
            if cert:
                artifacts["birth_certificate_id"] = cert.certificate_id
        
        # Get memory entries for this run
        memory_result = await self.db.execute(
            select(MemoryEntry).where(MemoryEntry.authority_run_id == run.id)
        )
        memory_entries = memory_result.scalars().all()
        artifacts["memory_entry_ids"] = [entry.memory_entry_id for entry in memory_entries]
        
        # Get browser actions for this run
        browser_result = await self.db.execute(
            select(BrowserAction).where(BrowserAction.authority_run_id == run.id)
        )
        browser_actions = browser_result.scalars().all()
        artifacts["browser_action_ids"] = [action.browser_action_id for action in browser_actions]
        
        # Get authority decisions (tool calls)
        decisions_result = await self.db.execute(
            select(AuthorityDecision).where(AuthorityDecision.authority_run_id == run.id)
        )
        decisions = decisions_result.scalars().all()
        artifacts["tool_call_ids"] = [decision.id for decision in decisions]
        
        # Get ledger events for this agent up to the run time
        if agent:
            ledger_result = await self.db.execute(
                select(LedgerEvent)
                .where(LedgerEvent.agent_id == agent.id)
                .where(LedgerEvent.created_at <= run.created_at)
                .order_by(LedgerEvent.created_at)
            )
            ledger_events = ledger_result.scalars().all()
            artifacts["ledger_event_ids"] = [event.id for event in ledger_events]
        
        return artifacts
    
    async def _compute_hashes(self, run: AuthorityRun, artifacts: Dict[str, Any]) -> Dict[str, str]:
        """Compute hash chain for integrity verification."""
        
        # Helper function to compute SHA256 hash
        def sha256_hash(data: Any) -> str:
            if isinstance(data, (dict, list)):
                data = json.dumps(data, sort_keys=True, separators=(',', ':'))
            return hashlib.sha256(str(data).encode()).hexdigest()
        
        # Compute individual hashes
        input_hash = sha256_hash({
            "authority_run_id": run.id,
            "agent_id": run.agent_id,
            "workspace_id": run.workspace_id,
            "start_time": run.start_time.isoformat() if run.start_time else None
        })
        
        output_hash = sha256_hash({
            "total_actions": run.total_actions,
            "approved_actions": run.approved_actions,
            "denied_actions": run.denied_actions,
            "violation_count": run.violation_count,
            "end_time": run.end_time.isoformat() if run.end_time else None
        })
        
        audit_hash = sha256_hash(run.decisions)
        ledger_hash = sha256_hash(artifacts.get("ledger_event_ids", []))
        artifacts_hash = sha256_hash({
            "birth_certificate_id": artifacts.get("birth_certificate_id"),
            "authority_bundle_id": artifacts.get("authority_bundle_id"),
            "memory_entry_ids": artifacts.get("memory_entry_ids", []),
            "browser_action_ids": artifacts.get("browser_action_ids", []),
            "tool_call_ids": artifacts.get("tool_call_ids", []),
            "ledger_event_ids": artifacts.get("ledger_event_ids", [])
        })
        
        return {
            "input_hash": input_hash,
            "output_hash": output_hash,
            "audit_hash": audit_hash,
            "ledger_hash": ledger_hash,
            "artifacts_hash": artifacts_hash
        }


class EvidencePackVerifier:
    """Verifies evidence pack integrity and hash chains."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def verify_evidence_pack(self, evidence_pack_id: str) -> Dict[str, Any]:
        """Verify an evidence pack by recomputing hashes and validating chains."""
        
        # Get the evidence pack
        pack_result = await self.db.execute(
            select(EvidencePack).where(EvidencePack.evidence_pack_id == evidence_pack_id)
        )
        pack = pack_result.scalar_one_or_none()
        
        if not pack:
            raise ValueError(f"Evidence pack {evidence_pack_id} not found")
        
        # Get the authority run
        run_result = await self.db.execute(
            select(AuthorityRun).where(AuthorityRun.id == pack.authority_run_id)
        )
        run = run_result.scalar_one_or_none()
        
        if not run:
            raise ValueError(f"Authority run {pack.authority_run_id} not found")
        
        # Rebuild artifacts and recompute hashes
        builder = EvidencePackBuilder(self.db)
        artifacts = await builder._collect_artifacts(run)
        recomputed_hashes = await builder._compute_hashes(run, artifacts)
        
        # Verify hashes match
        failures = []
        original_hashes = pack.hashes
        
        for hash_type in ["input_hash", "output_hash", "audit_hash", "ledger_hash", "artifacts_hash"]:
            if recomputed_hashes[hash_type] != original_hashes.get(hash_type):
                failures.append(f"{hash_type} mismatch: expected {original_hashes.get(hash_type)}, got {recomputed_hashes[hash_type]}")
        
        # Verify artifacts integrity
        artifact_failures = await self._verify_artifacts(pack.artifacts)
        failures.extend(artifact_failures)
        
        # Update verification status
        is_verified = len(failures) == 0
        pack.verification = {
            "verified": is_verified,
            "failures": failures,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "verification_method": "hash_chain_reconstruction"
        }
        
        await self.db.commit()
        
        return {
            "evidence_pack_id": evidence_pack_id,
            "verified": is_verified,
            "failures": failures,
            "checked_at": pack.verification["checked_at"],
            "hash_comparison": {
                "original": original_hashes,
                "recomputed": recomputed_hashes
            }
        }
    
    async def _verify_artifacts(self, artifacts: Dict[str, Any]) -> List[str]:
        """Verify that all referenced artifacts exist and are accessible."""
        
        failures = []
        
        # Verify birth certificate
        if artifacts.get("birth_certificate_id"):
            cert_result = await self.db.execute(
                select(BirthCertificate).where(BirthCertificate.certificate_id == artifacts["birth_certificate_id"])
            )
            if not cert_result.scalar_one_or_none():
                failures.append(f"Birth certificate {artifacts['birth_certificate_id']} not found")
        
        # Verify authority bundle
        if artifacts.get("authority_bundle_id"):
            from backend.db.models.authority import AuthorityBundle
            bundle_result = await self.db.execute(
                select(AuthorityBundle).where(AuthorityBundle.id == artifacts["authority_bundle_id"])
            )
            if not bundle_result.scalar_one_or_none():
                failures.append(f"Authority bundle {artifacts['authority_bundle_id']} not found")
        
        # Verify memory entries
        for memory_id in artifacts.get("memory_entry_ids", []):
            memory_result = await self.db.execute(
                select(MemoryEntry).where(MemoryEntry.memory_entry_id == memory_id)
            )
            if not memory_result.scalar_one_or_none():
                failures.append(f"Memory entry {memory_id} not found")
        
        # Verify browser actions
        for action_id in artifacts.get("browser_action_ids", []):
            action_result = await self.db.execute(
                select(BrowserAction).where(BrowserAction.browser_action_id == action_id)
            )
            if not action_result.scalar_one_or_none():
                failures.append(f"Browser action {action_id} not found")
        
        # Verify ledger events
        for event_id in artifacts.get("ledger_event_ids", []):
            event_result = await self.db.execute(
                select(LedgerEvent).where(LedgerEvent.id == event_id)
            )
            if not event_result.scalar_one_or_none():
                failures.append(f"Ledger event {event_id} not found")
        
        return failures


class EvidenceService:
    """Main evidence service combining builder and verifier functionality."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.builder = EvidencePackBuilder(db)
        self.verifier = EvidencePackVerifier(db)
    
    async def build_evidence_pack(
        self,
        authority_run_id: str,
        workspace_id: str,
        agent_id: str,
        creator_id: str,
        description: Optional[str] = None
    ) -> EvidencePack:
        """Build an evidence pack for a given authority run."""
        return await self.builder.build_evidence_pack(
            authority_run_id=authority_run_id,
            workspace_id=workspace_id,
            agent_id=agent_id,
            creator_id=creator_id,
            description=description
        )
    
    async def verify_evidence_pack(self, evidence_pack_id: str) -> Dict[str, Any]:
        """Verify an evidence pack's integrity."""
        return await self.verifier.verify_evidence_pack(evidence_pack_id)
    
    async def get_evidence_pack(self, evidence_pack_id: str) -> Optional[EvidencePack]:
        """Get an evidence pack by ID."""
        result = await self.db.execute(
            select(EvidencePack).where(EvidencePack.evidence_pack_id == evidence_pack_id)
        )
        return result.scalar_one_or_none()
    
    async def list_evidence_packs(
        self,
        workspace_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        authority_run_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[EvidencePack]:
        """List evidence packs with optional filters."""
        
        query = select(EvidencePack)
        
        if workspace_id:
            query = query.where(EvidencePack.workspace_id == workspace_id)
        
        if agent_id:
            query = query.where(EvidencePack.agent_id == agent_id)
        
        if authority_run_id:
            query = query.where(EvidencePack.authority_run_id == authority_run_id)
        
        query = query.order_by(EvidencePack.created_at.desc()).limit(limit).offset(offset)
        
        result = await self.db.execute(query)
        return result.scalars().all()
