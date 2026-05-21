"""
Agent Telemetry Service
For Veklom BYOS Backend

This service bridges scientist agents (063-067) and the GFR engine.
It also drives the oprun evidence trail via Agent-072 (Evidence).

Flow:
  Scientist agent (063-067)
      → POST /api/v1/gfr/telemetry
          → AgentTelemetryService.ingest()
              → gfr.update_field_node()     (update pressure)
              → gfr.snapshot()              (capture evidence)
              → EvidenceStore.record()       (write to oprun trail)

  Neural Orchestrator (Agent-129) / Gladiator (Agent-121)
      → POST /api/v1/gfr/route
          → AgentTelemetryService.route_workload()
              → gfr.route()                 (gradient descent routing)
              → EvidenceStore.record()       (log routing decision)
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Optional

from backend.core.services.gfr_engine import GFRSnapshot, gfr


@dataclass
class TelemetryRecord:
    agent_id: int
    agent_codename: str
    row: int
    col: int
    cpu_load: float        # 0.0 – 1.0
    queue_depth: float     # 0.0 – 1.0 (normalised)
    timestamp: str


@dataclass
class RoutingDecision:
    agent_id: int
    origin_row: int
    origin_col: int
    dest_row: int
    dest_col: int
    at_equilibrium: bool
    timestamp: str


class EvidenceStore:
    """
    In-process oprun evidence trail.
    Stores telemetry records and routing decisions so Agent-072
    can replay the load-balancing history.

    In production, replace _records with a Postgres INSERT via
    the existing EvidenceArtifact model (db/models/__init__.py).
    """

    def __init__(self, max_records: int = 10_000):
        self._records: list[dict] = []
        self._max = max_records

    def record(self, event_type: str, payload: dict) -> None:
        entry = {
            "event_type": event_type,
            "payload": payload,
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        }
        self._records.append(entry)
        # Ring-buffer: drop oldest when full
        if len(self._records) > self._max:
            self._records = self._records[-self._max:]

    def tail(self, n: int = 50) -> list[dict]:
        """Return the n most recent evidence records."""
        return self._records[-n:]

    def clear(self) -> None:
        self._records.clear()


# Module-level singletons
evidence_store = EvidenceStore()

# Scientist agent registry — maps agent_id to grid coordinates.
# Agents 063-067 are the telemetry producers.
SCIENTIST_AGENT_NODES: dict[int, tuple[int, int]] = {
    63: (0, 0),  # latency scientist
    64: (0, 1),  # memory scientist
    65: (0, 2),  # governance scientist
    66: (0, 3),  # telemetry scientist
    67: (0, 4),  # data transfer scientist
    68: (1, 0),  # UACP scientist
    69: (1, 1),  # cloud scientist
    70: (1, 2),  # marketplace scientist
    71: (1, 3),  # evidence scientist
    72: (1, 4),  # evidence agent (writes oprun trail)
}

# Special governance agents mapped to grid positions
SPECIAL_AGENT_NODES: dict[int, tuple[int, int]] = {
    120: (2, 0),  # Zeno Enforcer
    121: (2, 1),  # Gladiator Optimizer
    122: (2, 2),  # SSRN/ArXiv Discoverer
    123: (2, 3),  # Swarm Architect
    124: (2, 4),  # Quantum-Hybrid Builder
    125: (3, 0),  # RAG Sovereign
    126: (3, 1),  # Listener Nexus
    127: (3, 2),  # HRM Supreme
    128: (3, 3),  # Sentinel Prime
    129: (3, 4),  # Neural Orchestrator
}

ALL_AGENT_NODES = {**SCIENTIST_AGENT_NODES, **SPECIAL_AGENT_NODES}


class AgentTelemetryService:
    """Bridges scientist agents ↔ GFR ↔ evidence trail."""

    @staticmethod
    def resolve_node(agent_id: int, row: Optional[int], col: Optional[int]) -> tuple[int, int]:
        """Resolve grid coords: use registry if not explicitly provided."""
        if row is not None and col is not None:
            return (row, col)
        if agent_id in ALL_AGENT_NODES:
            return ALL_AGENT_NODES[agent_id]
        # Fallback: hash agent_id into grid
        grid = gfr.grid_size
        return (agent_id % grid, (agent_id // grid) % grid)

    @staticmethod
    def ingest(
        agent_id: int,
        agent_codename: str,
        cpu_load: float,
        queue_depth: float,
        row: Optional[int] = None,
        col: Optional[int] = None,
    ) -> GFRSnapshot:
        """
        Ingest telemetry from a scientist agent.
        Updates the GFR field, captures a snapshot, writes to evidence trail.
        Returns the snapshot for the API response.
        """
        r, c = AgentTelemetryService.resolve_node(agent_id, row, col)

        record = TelemetryRecord(
            agent_id=agent_id,
            agent_codename=agent_codename,
            row=r,
            col=c,
            cpu_load=cpu_load,
            queue_depth=queue_depth,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        # Update field
        gfr.update_field_node(
            row=r,
            col=c,
            cpu_load=cpu_load,
            queue_depth=queue_depth,
            triggered_by=agent_codename,
        )

        # Capture evidence snapshot
        snap = gfr.snapshot(triggered_by=agent_codename)

        # Write to oprun evidence trail
        evidence_store.record(
            event_type="telemetry_ingest",
            payload={
                "telemetry": asdict(record),
                "field_snapshot": {
                    "timestamp": snap.timestamp,
                    "active_nodes": snap.active_nodes,
                    "hotspot_count": snap.hotspot_count,
                },
            },
        )

        return snap

    @staticmethod
    def route_workload(
        agent_id: int,
        origin_row: Optional[int] = None,
        origin_col: Optional[int] = None,
    ) -> RoutingDecision:
        """
        Route a workload for the given agent.
        Called by Agent-121 (Gladiator), Agent-129 (Neural Orchestrator),
        and any scientist agent requesting optimal node placement.
        """
        r, c = AgentTelemetryService.resolve_node(agent_id, origin_row, origin_col)
        dest_r, dest_c = gfr.route(r, c)
        at_eq = (dest_r == r and dest_c == c)

        decision = RoutingDecision(
            agent_id=agent_id,
            origin_row=r,
            origin_col=c,
            dest_row=dest_r,
            dest_col=dest_c,
            at_equilibrium=at_eq,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        evidence_store.record(
            event_type="routing_decision",
            payload=asdict(decision),
        )

        return decision


# Module-level singleton
agent_telemetry = AgentTelemetryService()
