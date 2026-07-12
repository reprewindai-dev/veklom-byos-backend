"""Veklom Poltergeist Daemon.

Manages the anticipatory build queue (Deduplicating Build Queue) and the Freshness Gate
for GPC Pipeline capabilities. 
"""

import asyncio
import traceback
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy import select, update
from loguru import logger

from backend.core.database.database import async_session
from backend.db.models.poltergeist import CapabilityHauntState, CapabilityGhost
from backend.core.services.poltergeist_registry import poltergeist_registry
from backend.core.services.r2_storage import r2_storage


class CompilerFreshnessGate:
    """Blocks finalization of GPC pipelines until capabilities are fresh."""
    
    @staticmethod
    async def wait_for_freshness(fingerprint: str, required_revision: int, timeout_seconds: int = 60) -> bool:
        """
        Polls the registry/database until the capability is fresh or timeouts.
        Returns True if fresh, False if timeout.
        """
        start_time = asyncio.get_event_loop().time()
        
        while asyncio.get_event_loop().time() - start_time < timeout_seconds:
            # Check fast Redis memory first
            hot_state = await poltergeist_registry.get_capability_state(fingerprint)
            if hot_state and hot_state.get("status") == "fresh" and hot_state.get("freshest_artifact_revision", 0) >= required_revision:
                return True
                
            # Fallback to DB
            async with async_session() as db:
                haunt = (await db.execute(
                    select(CapabilityHauntState).where(CapabilityHauntState.fingerprint == fingerprint)
                )).scalar_one_or_none()
                
                if haunt and haunt.status == "fresh" and haunt.freshest_artifact_revision >= required_revision:
                    return True
                    
            await asyncio.sleep(1)
            
        return False


class PoltergeistDaemon:
    """Background service managing speculative builds of capabilities."""
    
    def __init__(self):
        self._running = False
        self._task: Optional[asyncio.Task] = None
        
    def start(self):
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._daemon_loop(), name="veklom-poltergeist-daemon")
        logger.info("[poltergeist] daemon started")
        
    def stop(self):
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
        logger.info("[poltergeist] daemon stopped")

    async def submit_intent(self, workspace_id: str, fingerprint: str, required_revision: int, manifest: Dict[str, Any]):
        """Deduplicating Build Queue: merge overlapping intent requests."""
        async with async_session() as db:
            haunt = (await db.execute(
                select(CapabilityHauntState).where(CapabilityHauntState.fingerprint == fingerprint)
            )).scalar_one_or_none()
            
            if haunt:
                if required_revision > haunt.queued_revision:
                    haunt.queued_revision = required_revision
                    # If it was idle/failed, or even fresh but now stale, push back to idle to trigger rebuild
                    if haunt.status in ("failed", "fresh", "idle"):
                        haunt.status = "idle"
                    await db.commit()
                    logger.info(f"[poltergeist] Updated intent for {fingerprint} to revision {required_revision}")
            else:
                new_haunt = CapabilityHauntState(
                    workspace_id=workspace_id,
                    fingerprint=fingerprint,
                    status="idle",
                    queued_revision=required_revision,
                    freshest_artifact_revision=0
                )
                db.add(new_haunt)
                await db.commit()
                logger.info(f"[poltergeist] Queued new intent for {fingerprint} (rev {required_revision})")
                
            # Update hot memory
            await poltergeist_registry.set_capability_state(fingerprint, {
                "status": "idle",
                "queued_revision": required_revision
            })

    async def _daemon_loop(self):
        """Polls for idle/pending capability builds."""
        # Wait a moment on startup
        await asyncio.sleep(5)
        logger.info("[poltergeist] daemon loop active")
        
        while self._running:
            try:
                await self._process_idle_haunts()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[poltergeist] daemon error: {e}")
                traceback.print_exc()
                
            await asyncio.sleep(2)  # fast polling for reactivity

    async def _process_idle_haunts(self):
        """Find capabilities needing builds and route them."""
        async with async_session() as db:
            # Find targets: idle, or where queued > freshest
            result = await db.execute(
                select(CapabilityHauntState)
                .where(
                    (CapabilityHauntState.status == "idle") |
                    (CapabilityHauntState.queued_revision > CapabilityHauntState.freshest_artifact_revision)
                )
                .limit(10)
            )
            haunts = result.scalars().all()
            
            for haunt in haunts:
                # Attempt distributed lock
                if await poltergeist_registry.acquire_build_lock(haunt.fingerprint, ttl_seconds=300):
                    # Transition to resolving
                    haunt.status = "resolving"
                    await db.commit()
                    
                    # Update hot state
                    await poltergeist_registry.set_capability_state(haunt.fingerprint, {
                        "status": "resolving",
                        "queued_revision": haunt.queued_revision
                    })
                    
                    # Fire-and-forget the build task to the worker pool
                    asyncio.create_task(self._simulate_agent_build(haunt.fingerprint, haunt.queued_revision, haunt.workspace_id))

    async def _simulate_agent_build(self, fingerprint: str, target_revision: int, workspace_id: str):
        """
        Phase 3: Autonomous Builder Hook
        This simulates the agent generating, testing, and RepoGate scanning the capability.
        """
        logger.info(f"[poltergeist] Agent workforce engaged for {fingerprint} (rev {target_revision})")
        
        # 1. Update status to building
        await self._update_haunt_status(fingerprint, "building")
        await asyncio.sleep(2) # Simulate LLM gen
        
        # 2. Update status to testing
        await self._update_haunt_status(fingerprint, "testing")
        await asyncio.sleep(1) # Simulate test run
        
        # 3. Verifying (RepoGate + PGL)
        await self._update_haunt_status(fingerprint, "verifying")
        await asyncio.sleep(1)
        
        verification_results = {
            "repogate": "pass",
            "pgl": "pass",
            "unit_tests": "pass"
        }
        
        # 4. Success -> Dump to R2 & Update Postgres
        mock_wasm_body = b"\\x00asm...mock...body..."
        artifact_ptr = await r2_storage.upload_artifact(
            fingerprint, target_revision, mock_wasm_body, "runtime.wasm"
        )
        
        async with async_session() as db:
            # Create permanent ghost
            ghost = CapabilityGhost(
                workspace_id=workspace_id,
                fingerprint=fingerprint,
                revision=target_revision,
                artifact_pointer=artifact_ptr or ""
            )
            db.add(ghost)
            
            # Update haunt state to fresh
            haunt = (await db.execute(
                select(CapabilityHauntState).where(CapabilityHauntState.fingerprint == fingerprint)
            )).scalar_one_or_none()
            
            if haunt:
                haunt.status = "fresh"
                haunt.freshest_artifact_revision = target_revision
                haunt.verification_results = verification_results
                
            await db.commit()
            
            # Update hot memory
            await poltergeist_registry.set_capability_state(fingerprint, {
                "status": "fresh",
                "freshest_artifact_revision": target_revision,
                "verification_results": verification_results
            })
            
        logger.info(f"[poltergeist] Capability {fingerprint} (rev {target_revision}) is now FRESH.")
        
        # Release lock
        await poltergeist_registry.release_build_lock(fingerprint)

    async def _update_haunt_status(self, fingerprint: str, status: str):
        """Helper to quickly update DB and Redis state."""
        async with async_session() as db:
            haunt = (await db.execute(
                select(CapabilityHauntState).where(CapabilityHauntState.fingerprint == fingerprint)
            )).scalar_one_or_none()
            if haunt:
                haunt.status = status
                await db.commit()
                
        await poltergeist_registry.set_capability_state(fingerprint, {"status": status})

poltergeist_daemon = PoltergeistDaemon()
