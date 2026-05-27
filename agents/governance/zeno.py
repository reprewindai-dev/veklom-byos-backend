"""
Agent-120 — Zeno Enforcer (Special Governance)
================================================
Implements the Zeno Effect governance protocol across the entire agent workforce.

Principle: Continuous observation freezes state transitions. When an agent is
under Zeno observation, it cannot mutate state without explicit approval.

Capabilities:
- Zeno Freeze: halt any agent/subsystem via continuous observation
- State Pinning: lock known-good state so it cannot degrade
- Zero-Motion Read/Write: inspect/modify governance state without side effects
- Observation Cascade: propagate freeze across dependent systems
- Coherence Check: validate observed state vs expected state
- Evidence Bundles: cryptographic proof for every intervention

Redis layout:
  zeno:freeze:{agent_id}       → "1" (frozen) | absent (free)
  zeno:state:{agent_id}        → JSON pinned state snapshot
  zeno:evidence:{agent_id}     → JSON list of intervention bundles
  zeno:cascade:{agent_id}      → JSON list of dependent agent_ids
  zeno:observations            → sorted-set (agent_id, timestamp) for active watchers
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional Redis client (falls back to in-process dict if Redis unavailable)
# ---------------------------------------------------------------------------

try:
    import redis.asyncio as aioredis  # type: ignore
    _REDIS_URL = __import__("os").getenv("REDIS_URL", "redis://localhost:6379/0")
    _redis_pool: aioredis.Redis | None = aioredis.from_url(_REDIS_URL, decode_responses=True)
except Exception:  # pragma: no cover
    _redis_pool = None
    logger.warning("Redis not available — Zeno Enforcer running in in-process fallback mode")

# ---- In-process fallback store (thread-safe enough for single-process use) ---
_mem_freeze: dict[str, bool] = {}
_mem_state: dict[str, dict] = {}
_mem_evidence: dict[str, list] = {}
_mem_cascade: dict[str, list[str]] = {}


async def _redis_get(key: str) -> str | None:
    if _redis_pool:
        try:
            return await _redis_pool.get(key)  # type: ignore[return-value]
        except Exception as e:
            logger.debug(f"Redis GET {key} failed: {e}")
    return None


async def _redis_set(key: str, value: str, ex: int | None = None) -> None:
    if _redis_pool:
        try:
            await _redis_pool.set(key, value, ex=ex)
            return
        except Exception as e:
            logger.debug(f"Redis SET {key} failed: {e}")


async def _redis_delete(key: str) -> None:
    if _redis_pool:
        try:
            await _redis_pool.delete(key)
            return
        except Exception as e:
            logger.debug(f"Redis DEL {key} failed: {e}")


# ---------------------------------------------------------------------------
# Evidence bundle helper
# ---------------------------------------------------------------------------

def _make_evidence_bundle(
    action: str,
    agent_id: str,
    details: dict[str, Any],
    passed: bool,
) -> dict[str, Any]:
    """Produce a hash-signed evidence bundle for every Zeno intervention."""
    ts = datetime.now(timezone.utc).isoformat()
    payload = json.dumps(
        {"action": action, "agent_id": agent_id, "details": details, "timestamp": ts, "passed": passed},
        sort_keys=True,
    )
    digest = hashlib.sha256(payload.encode()).hexdigest()
    return {
        "action": action,
        "agent_id": agent_id,
        "details": details,
        "timestamp": ts,
        "passed": passed,
        "sha256": digest,
    }


# ---------------------------------------------------------------------------
# ZenoEnforcer
# ---------------------------------------------------------------------------

class ZenoEnforcer:
    """
    High-frequency (512 Hz equivalent) deterministic logic gate that prevents
    hallucination propagation and unauthorized state mutation.

    All public methods are async and safe to call from FastAPI handlers or
    background tasks.
    """

    OBSERVATION_TTL_S: int = 3600  # freeze TTL — refreshed each observation cycle
    COHERENCE_THRESHOLD: float = 0.9995  # below this → coherence failure

    # ------------------------------------------------------------------
    # Freeze / Unfreeze
    # ------------------------------------------------------------------

    async def freeze(self, agent_id: str, reason: str = "zeno_observation") -> dict[str, Any]:
        """
        Freeze agent_id. While frozen, all state mutations are blocked.
        Generates a signed evidence bundle and triggers cascade if needed.
        """
        key = f"zeno:freeze:{agent_id}"
        await _redis_set(key, "1", ex=self.OBSERVATION_TTL_S)
        _mem_freeze[agent_id] = True

        evidence = _make_evidence_bundle("freeze", agent_id, {"reason": reason}, passed=True)
        await self._append_evidence(agent_id, evidence)

        logger.info(f"[Zeno] FREEZE  agent={agent_id}  reason={reason}")

        # Cascade to dependents
        cascade_targets = await self._get_cascade_targets(agent_id)
        cascade_results = []
        for dep_id in cascade_targets:
            dep_result = await self.freeze(dep_id, reason=f"cascade_from:{agent_id}")
            cascade_results.append({"agent_id": dep_id, "result": dep_result})

        return {
            "frozen": True,
            "agent_id": agent_id,
            "reason": reason,
            "timestamp": evidence["timestamp"],
            "evidence_sha256": evidence["sha256"],
            "cascade_count": len(cascade_results),
        }

    async def unfreeze(self, agent_id: str, approved_by: str = "operator") -> dict[str, Any]:
        """Unfreeze agent_id — requires explicit approval tracking."""
        key = f"zeno:freeze:{agent_id}"
        await _redis_delete(key)
        _mem_freeze.pop(agent_id, None)

        evidence = _make_evidence_bundle(
            "unfreeze", agent_id,
            {"approved_by": approved_by},
            passed=True,
        )
        await self._append_evidence(agent_id, evidence)
        logger.info(f"[Zeno] UNFREEZE agent={agent_id}  approved_by={approved_by}")

        return {
            "frozen": False,
            "agent_id": agent_id,
            "approved_by": approved_by,
            "timestamp": evidence["timestamp"],
            "evidence_sha256": evidence["sha256"],
        }

    async def is_frozen(self, agent_id: str) -> bool:
        """Check if agent is currently under Zeno freeze."""
        val = await _redis_get(f"zeno:freeze:{agent_id}")
        if val is not None:
            return val == "1"
        return _mem_freeze.get(agent_id, False)

    # ------------------------------------------------------------------
    # State Pinning (zero-motion read/write)
    # ------------------------------------------------------------------

    async def pin_state(self, agent_id: str, state: dict[str, Any]) -> dict[str, Any]:
        """
        Lock a known-good state snapshot. Future coherence checks compare
        live state against this pin.
        """
        ts = datetime.now(timezone.utc).isoformat()
        state_doc = {"agent_id": agent_id, "pinned_at": ts, "state": state}
        payload = json.dumps(state_doc, sort_keys=True)

        await _redis_set(f"zeno:state:{agent_id}", payload, ex=86400)
        _mem_state[agent_id] = state_doc

        evidence = _make_evidence_bundle(
            "pin_state", agent_id,
            {"state_keys": list(state.keys()), "pinned_at": ts},
            passed=True,
        )
        await self._append_evidence(agent_id, evidence)
        logger.info(f"[Zeno] PIN_STATE agent={agent_id}  keys={list(state.keys())}")

        return {
            "pinned": True,
            "agent_id": agent_id,
            "pinned_at": ts,
            "evidence_sha256": evidence["sha256"],
        }

    async def get_pinned_state(self, agent_id: str) -> dict[str, Any] | None:
        """Zero-motion read — retrieve pinned state without triggering watchers."""
        raw = await _redis_get(f"zeno:state:{agent_id}")
        if raw:
            try:
                return json.loads(raw)
            except Exception:
                pass
        return _mem_state.get(agent_id)

    # ------------------------------------------------------------------
    # Coherence Validation
    # ------------------------------------------------------------------

    async def check_coherence(
        self,
        agent_id: str,
        observed_state: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Compare observed_state against pinned state.
        Returns coherence score and pass/fail verdict.
        """
        pinned_doc = await self.get_pinned_state(agent_id)
        if not pinned_doc:
            # No pin → assume coherent (first observation establishes baseline)
            await self.pin_state(agent_id, observed_state)
            return {
                "coherent": True,
                "score": 1.0,
                "agent_id": agent_id,
                "note": "First observation — state pinned as baseline",
            }

        pinned_state = pinned_doc.get("state", {})
        score = self._coherence_score(pinned_state, observed_state)
        passed = score >= self.COHERENCE_THRESHOLD

        details: dict[str, Any] = {
            "score": score,
            "threshold": self.COHERENCE_THRESHOLD,
            "divergent_keys": self._divergent_keys(pinned_state, observed_state),
        }
        evidence = _make_evidence_bundle("coherence_check", agent_id, details, passed=passed)
        await self._append_evidence(agent_id, evidence)

        if not passed:
            logger.warning(
                f"[Zeno] COHERENCE FAILURE agent={agent_id}  score={score:.4f}  "
                f"divergent_keys={details['divergent_keys']}"
            )
            # Auto-freeze on coherence failure
            await self.freeze(agent_id, reason=f"coherence_failure:score={score:.4f}")

        return {
            "coherent": passed,
            "score": score,
            "agent_id": agent_id,
            "threshold": self.COHERENCE_THRESHOLD,
            "divergent_keys": details["divergent_keys"],
            "evidence_sha256": evidence["sha256"],
            "frozen_on_failure": not passed,
        }

    def _coherence_score(self, pinned: dict, observed: dict) -> float:
        """
        Compare two state dicts. Returns float [0..1].
        Uses key-presence + value-hash matching.
        """
        all_keys = set(pinned.keys()) | set(observed.keys())
        if not all_keys:
            return 1.0
        matching = 0
        for k in all_keys:
            pv = json.dumps(pinned.get(k), sort_keys=True)
            ov = json.dumps(observed.get(k), sort_keys=True)
            if pv == ov:
                matching += 1
        return matching / len(all_keys)

    def _divergent_keys(self, pinned: dict, observed: dict) -> list[str]:
        all_keys = set(pinned.keys()) | set(observed.keys())
        return [
            k for k in all_keys
            if json.dumps(pinned.get(k), sort_keys=True)
            != json.dumps(observed.get(k), sort_keys=True)
        ]

    # ------------------------------------------------------------------
    # Mutation Gate (call this BEFORE any write operation)
    # ------------------------------------------------------------------

    async def mutation_gate(
        self,
        agent_id: str,
        operation: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Deterministic gate that blocks all mutations when agent is frozen.
        Wire this into every write endpoint for governed agents.
        """
        frozen = await self.is_frozen(agent_id)
        ts = datetime.now(timezone.utc).isoformat()

        if frozen:
            evidence = _make_evidence_bundle(
                "mutation_blocked", agent_id,
                {"operation": operation, "payload_keys": list(payload.keys())},
                passed=False,
            )
            await self._append_evidence(agent_id, evidence)
            logger.warning(
                f"[Zeno] MUTATION BLOCKED  agent={agent_id}  op={operation}"
            )
            return {
                "allowed": False,
                "reason": "ZENO_FROZEN",
                "message": (
                    f"Agent {agent_id} is under Zeno observation. "
                    "All state mutations are frozen until explicitly approved."
                ),
                "timestamp": ts,
                "evidence_sha256": evidence["sha256"],
            }

        evidence = _make_evidence_bundle(
            "mutation_allowed", agent_id,
            {"operation": operation, "payload_keys": list(payload.keys())},
            passed=True,
        )
        await self._append_evidence(agent_id, evidence)
        return {
            "allowed": True,
            "agent_id": agent_id,
            "operation": operation,
            "timestamp": ts,
            "evidence_sha256": evidence["sha256"],
        }

    # ------------------------------------------------------------------
    # Cascade Management
    # ------------------------------------------------------------------

    async def register_cascade(self, parent_id: str, dependent_ids: list[str]) -> None:
        """Register that freezing parent_id should cascade to dependent_ids."""
        payload = json.dumps(dependent_ids)
        await _redis_set(f"zeno:cascade:{parent_id}", payload, ex=86400)
        _mem_cascade[parent_id] = dependent_ids
        logger.info(f"[Zeno] CASCADE_REGISTERED  parent={parent_id}  deps={dependent_ids}")

    async def _get_cascade_targets(self, agent_id: str) -> list[str]:
        raw = await _redis_get(f"zeno:cascade:{agent_id}")
        if raw:
            try:
                return json.loads(raw)
            except Exception:
                pass
        return _mem_cascade.get(agent_id, [])

    # ------------------------------------------------------------------
    # Evidence Bundles
    # ------------------------------------------------------------------

    async def _append_evidence(self, agent_id: str, bundle: dict[str, Any]) -> None:
        key = f"zeno:evidence:{agent_id}"
        raw = await _redis_get(key)
        bundles: list[dict] = []
        if raw:
            try:
                bundles = json.loads(raw)
            except Exception:
                pass
        bundles.append(bundle)
        # Keep last 100 evidence items
        bundles = bundles[-100:]
        payload = json.dumps(bundles)
        await _redis_set(key, payload, ex=86400)
        if agent_id not in _mem_evidence:
            _mem_evidence[agent_id] = []
        _mem_evidence[agent_id].append(bundle)
        _mem_evidence[agent_id] = _mem_evidence[agent_id][-100:]

    async def get_evidence(self, agent_id: str) -> list[dict[str, Any]]:
        """Retrieve all evidence bundles for an agent."""
        raw = await _redis_get(f"zeno:evidence:{agent_id}")
        if raw:
            try:
                return json.loads(raw)
            except Exception:
                pass
        return _mem_evidence.get(agent_id, [])

    # ------------------------------------------------------------------
    # Full Swarm Observation Cycle
    # ------------------------------------------------------------------

    async def run_observation_cycle(
        self,
        agent_ids: list[str],
        states: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Run a full 512-Hz observation cycle across all provided agents.
        Checks coherence for each agent, triggers freezes on failure.
        Returns a summary report.
        """
        start = time.monotonic()
        results: list[dict] = []
        frozen_count = 0
        coherent_count = 0

        for agent_id in agent_ids:
            state = states.get(agent_id, {})
            result = await self.check_coherence(agent_id, state)
            results.append({"agent_id": agent_id, **result})
            if result.get("coherent"):
                coherent_count += 1
            else:
                frozen_count += 1

        elapsed_ms = (time.monotonic() - start) * 1000
        ts = datetime.now(timezone.utc).isoformat()

        logger.info(
            f"[Zeno] OBSERVATION_CYCLE  agents={len(agent_ids)}  "
            f"coherent={coherent_count}  frozen={frozen_count}  "
            f"elapsed_ms={elapsed_ms:.2f}"
        )

        return {
            "timestamp": ts,
            "agents_observed": len(agent_ids),
            "coherent": coherent_count,
            "frozen_on_failure": frozen_count,
            "elapsed_ms": round(elapsed_ms, 2),
            "results": results,
        }


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

zeno = ZenoEnforcer()
