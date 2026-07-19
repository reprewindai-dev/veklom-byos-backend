"""Veklom Poltergeist Daemon.

Manages the anticipatory build queue (Deduplicating Build Queue) and the Freshness Gate
for GPC Pipeline capabilities.

Also runs a self-healing InfrastructureSentinel that monitors:
  - Alembic migration head validity (auto-stamps stale heads)
  - Backend health endpoint (restarts container on sustained failure)
  - Disk usage (prunes Docker caches when disk exceeds 90%)
"""

import asyncio
import traceback
import logging
import os
import shutil
import subprocess
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Set
from sqlalchemy import select, update, text
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger("poltergeist_daemon")

from backend.core.database.database import async_session
from backend.db.models.poltergeist import CapabilityHauntState, CapabilityGhost
from backend.core.services.poltergeist_registry import poltergeist_registry
from backend.core.services.local_storage import local_storage


# ---------------------------------------------------------------------------
# Infrastructure Sentinel — self-healing background worker
# ---------------------------------------------------------------------------

class InfrastructureSentinel:
    """
    Runs autonomously alongside the GPC build daemon.
    Catches and recovers from infrastructure failures so the operator
    never has to SSH in to unblock deployments.

    Jobs (every 60 s unless a failure requires immediate action):
    1. Migration Guard   — stamps stale alembic_version heads so the
                           container can start after a bad migration push.
    2. Health Sentinel   — pings /health; auto-restarts the container on
                           sustained failure (> 90 s dark).
    3. Disk Watchdog     — prunes Docker build-cache + dangling images when
                           disk usage exceeds 90 %.
    """

    # The set of revision IDs that actually exist in the codebase.
    # Loaded lazily from alembic's script directory.
    _KNOWN_HEADS: Optional[Set[str]] = None

    HEALTH_URL = "http://127.0.0.1/health"
    HEALTH_DARK_THRESHOLD_S = 90   # seconds before we restart the container
    DISK_PRUNE_THRESHOLD_PCT = 90  # %
    POLL_INTERVAL_S = 60

    def __init__(self):
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._health_dark_since: Optional[float] = None  # epoch seconds
        self.is_degraded = False

    def start(self):
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(
            self._sentinel_loop(), name="veklom-infrastructure-sentinel"
        )
        logger.info("[sentinel] infrastructure sentinel started")

    def stop(self):
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
        logger.info("[sentinel] infrastructure sentinel stopped")

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    async def _sentinel_loop(self):
        await asyncio.sleep(15)  # give the container time to finish boot
        logger.info("[sentinel] sentinel loop active")

        while self._running:
            try:
                await asyncio.gather(
                    self._migration_guard(),
                    self._health_sentinel(),
                    self._disk_watchdog(),
                    return_exceptions=True,  # one failure must not kill the others
                )
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error(f"[sentinel] unexpected error in sentinel loop: {exc}")
                traceback.print_exc()

            await asyncio.sleep(self.POLL_INTERVAL_S)

    # ------------------------------------------------------------------
    # Job 1 — Migration Guard
    # ------------------------------------------------------------------

    async def _migration_guard(self):
        """
        Compares the alembic_version rows in Postgres against the
        revision IDs that actually exist on disk. Any row whose
        version_num is NOT in the known-heads set is a stale ghost that
        prevents startup — we stamp it to the latest real head.
        """
        try:
            known = self._load_known_heads()
            if not known:
                return  # can't determine heads — skip safely

            from backend.core.database.database import async_session as _session
            async with _session() as db:
                rows = (await db.execute(text("SELECT version_num FROM alembic_version"))).fetchall()
                for row in rows:
                    rev = row[0]
                    if rev not in known:
                        latest = max(known)  # lexicographic latest
                        logger.warning(
                            f"[sentinel][migration-guard] stale head detected: {rev!r} "
                            f"not in codebase. Stamping to {latest!r}."
                        )
                        await db.execute(
                            text("UPDATE alembic_version SET version_num = :latest WHERE version_num = :stale"),
                            {"latest": latest, "stale": rev},
                        )
                        await db.commit()
                        logger.info(f"[sentinel][migration-guard] ✓ stamped {rev!r} → {latest!r}")
        except Exception as exc:
            logger.error(f"[sentinel][migration-guard] error: {exc}")

    @classmethod
    def _load_known_heads(cls) -> Set[str]:
        """Walk the Alembic versions directory and return all known revision IDs."""
        if cls._KNOWN_HEADS is not None:
            return cls._KNOWN_HEADS
        try:
            import re
            versions_dir = os.path.join(
                os.path.dirname(__file__),
                "..", "..", "db", "migrations", "versions"
            )
            versions_dir = os.path.normpath(versions_dir)
            heads: Set[str] = set()
            for fname in os.listdir(versions_dir):
                if not fname.endswith(".py"):
                    continue
                # Extract revision id from filename heuristic (first 12-char hex segment)
                m = re.search(r"([0-9a-f]{12,})", fname)
                if m:
                    heads.add(m.group(1))
            cls._KNOWN_HEADS = heads
            logger.info(f"[sentinel][migration-guard] known heads: {heads}")
            return heads
        except Exception as exc:
            logger.warning(f"[sentinel][migration-guard] could not load known heads: {exc}")
            return set()

    # ------------------------------------------------------------------
    # Job 2 — Health Sentinel
    # ------------------------------------------------------------------

    async def _health_sentinel(self):
        """
        Pings /health. If the endpoint is dark for > HEALTH_DARK_THRESHOLD_S
        seconds we attempt a container self-restart via supervisord/uvicorn
        signal, BUT ONLY if the database is healthy (to avoid restart loops
        when DB is down).
        """
        db_healthy = False
        try:
            from backend.core.database.database import get_db_status
            status = await get_db_status()
            db_healthy = status.get("status") == "healthy"
        except Exception:
            pass

        try:
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as http:
                resp = await http.get(self.HEALTH_URL)
            if resp.status_code < 400:
                self._health_dark_since = None  # reset — we're healthy
                return
        except Exception:
            pass  # connection error also counts as dark

        now = asyncio.get_event_loop().time()
        if self._health_dark_since is None:
            self._health_dark_since = now
            logger.warning("[sentinel][health] /health is dark — watching...")
            return

        dark_for = now - self._health_dark_since
        logger.warning(f"[sentinel][health] /health dark for {dark_for:.0f}s")

        if dark_for >= self.HEALTH_DARK_THRESHOLD_S:
            if not db_healthy:
                logger.warning("[sentinel][health] threshold exceeded, but DB is down. Waiting instead of restarting.")
                return
                
            logger.error(
                "[sentinel][health] threshold exceeded and DB is healthy — attempting graceful restart"
            )
            try:
                # Inside the container: send SIGHUP to uvicorn (PID 1 or main worker)
                # Uvicorn treats SIGHUP as a reload signal.
                os.kill(1, 1)  # signal.SIGHUP = 1
                self._health_dark_since = None
                logger.info("[sentinel][health] SIGHUP sent to PID 1 — reloading")
            except Exception as exc:
                logger.error(f"[sentinel][health] could not send SIGHUP: {exc}")

    # ------------------------------------------------------------------
    # Job 3 — Disk Watchdog
    # ------------------------------------------------------------------

    async def _disk_watchdog(self):
        """
        Checks disk usage on /. If above threshold, prunes Docker build
        cache and dangling images to recover space.
        """
        try:
            target_path = os.environ.get("SENTINEL_DISK_PATH", "/")
            if not os.path.exists(target_path):
                logger.info(f"[sentinel][disk] path {target_path} not accessible, skipping watchdog")
                return

            usage = shutil.disk_usage(target_path)
            pct = (usage.used / usage.total) * 100
            if pct < self.DISK_PRUNE_THRESHOLD_PCT:
                self.is_degraded = False
                return

            logger.warning(
                f"[sentinel][disk] disk at {pct:.1f}% — pruning Docker caches"
            )
            self.is_degraded = True
            loop = asyncio.get_event_loop()
            # Run in thread pool so we don't block the event loop
            await loop.run_in_executor(
                None,
                lambda: subprocess.run(
                    ["docker", "system", "prune", "-f", "--filter", "until=1440h"],
                    capture_output=True, timeout=120
                )
            )
            new_usage = shutil.disk_usage(target_path)
            new_pct = (new_usage.used / new_usage.total) * 100
            self.is_degraded = new_pct >= self.DISK_PRUNE_THRESHOLD_PCT
            logger.info(
                f"[sentinel][disk] after prune: {new_pct:.1f}% "
                f"(freed {(usage.used - new_usage.used) / 1e9:.2f} GB)"
            )
        except Exception as exc:
            logger.error(f"[sentinel][disk] disk watchdog error: {exc}")
            self.is_degraded = True


# Singleton
infrastructure_sentinel = InfrastructureSentinel()


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
        # Also spin up the self-healing infrastructure sentinel
        infrastructure_sentinel.start()
        logger.info("[poltergeist] daemon started")
        
    def stop(self):
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
        infrastructure_sentinel.stop()
        logger.info("[poltergeist] daemon stopped")

    async def submit_intent(self, workspace_id: str, fingerprint: str, required_revision: int, manifest: Dict[str, Any]):
        """Deduplicating Build Queue: merge overlapping intent requests."""
        # Update hot memory first for immediate reads
        await poltergeist_registry.set_capability_state(fingerprint, {
            "status": "idle",
            "queued_revision": required_revision
        })
        
        async with async_session() as db:
            haunt = (await db.execute(
                select(CapabilityHauntState).where(CapabilityHauntState.fingerprint == fingerprint)
            )).scalar_one_or_none()
            
            if haunt:
                if required_revision > haunt.queued_revision:
                    haunt.queued_revision = required_revision
                    haunt.manifest = manifest
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
                    freshest_artifact_revision=0,
                    manifest=manifest
                )
                db.add(new_haunt)
                try:
                    await db.commit()
                    logger.info(f"[poltergeist] Queued new intent for {fingerprint} (rev {required_revision})")
                except IntegrityError:
                    await db.rollback()
                    # A concurrent request created it first. Fetch and update.
                    haunt = (await db.execute(
                        select(CapabilityHauntState).where(CapabilityHauntState.fingerprint == fingerprint)
                    )).scalar_one_or_none()
                    if haunt and required_revision > haunt.queued_revision:
                        haunt.queued_revision = required_revision
                        haunt.manifest = manifest
                        if haunt.status in ("failed", "fresh", "idle"):
                            haunt.status = "idle"
                        await db.commit()
                        logger.info(f"[poltergeist] Concurrently updated intent for {fingerprint} to revision {required_revision}")

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
                    asyncio.create_task(self._execute_agent_build(haunt.fingerprint, haunt.queued_revision, haunt.workspace_id))

    async def _execute_agent_build(self, fingerprint: str, target_revision: int, workspace_id: str):
        """
        Phase 2B: Real Autonomous Builder Hooks
        Invokes the actual coordinator to generate, test, and scan the capability.
        """
        from backend.ops.builders.coordinator import AutonomousBuilderCoordinator
        
        logger.info(f"[poltergeist] Agent workforce engaged for {fingerprint} (rev {target_revision})")
        
        # 1. Fetch dynamic manifest from DB and update status
        manifest = {}
        async with async_session() as db:
            haunt = (await db.execute(
                select(CapabilityHauntState).where(CapabilityHauntState.fingerprint == fingerprint)
            )).scalar_one_or_none()
            if haunt:
                manifest = haunt.manifest or {}
                
        await self._update_haunt_status(fingerprint, "building")
        
        # Fallback to python transform if manifest is somehow missing
        if not manifest:
            manifest = {
                "type": "python_transform",
                "engine": "duckdb"
            }
        
        # 2. Execute Real Build
        is_valid, verification_results, artifact_bytes = await AutonomousBuilderCoordinator.build_capability(
            fingerprint, target_revision, manifest
        )
        
        if not is_valid:
            logger.error(f"[poltergeist] Build failed for {fingerprint}")
            await self._update_haunt_status(fingerprint, "failed")
            await poltergeist_registry.release_build_lock(fingerprint)
            return
            
        # 3. Success -> Dump to NVMe & Update Postgres
        artifact_ptr = await local_storage.upload_artifact(
            fingerprint, target_revision, artifact_bytes, "capability.zip"
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
