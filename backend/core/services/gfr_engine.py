"""
Gradient Field Router (GFR) — Load Balancing Skill
For Veklom BYOS Backend

Consumed by:
  - Agent-121 (Gladiator Optimizer)  — swarm cost routing
  - Agent-122 (SSRN/ArXiv Discoverer) — paper-fetch job routing
  - Agent-123 (Swarm Architect)       — valve topology decisions
  - Agent-124 (Quantum-Hybrid Builder) — heavy compute routing
  - Agent-129 (Neural Orchestrator)   — macro budget/routing decisions
  - Scientist agents 063-067          — produce telemetry consumed here

Governance Gate:
  np.clip(field, FLOOR_VALUE, None) is applied before EVERY gradient
  computation. This prevents gravity sinks / infinite potential wells
  that would trap all traffic into a runaway bottleneck node.

Math:
  - Potential field  φ(x,y) = α·cpu_load(x,y) + β·queue_depth(x,y)
  - Gradient        ∇φ = np.gradient(φ)   # boundary-safe, O(n) vectorized
  - Normalized dir  d = -∇φ / ||∇φ||      # steepest descent, unit vector
  - Equilibrium     ||∇φ|| ≈ 0 → return [0,0]  (already at minimum)
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import numpy as np

# --- Constants ---
FLOOR_VALUE: float = 0.01          # Governance gate: prevents gravity sinks
EQUILIBRIUM_THRESHOLD: float = 1e-6  # ||∇φ|| below this → at rest
CPU_WEIGHT: float = 0.7            # α — weight for CPU load component
QUEUE_WEIGHT: float = 0.3          # β — weight for queue depth component
DEFAULT_GRID_SIZE: int = 10        # Default NxN cluster matrix dimension


@dataclass
class GFRSnapshot:
    """Immutable field snapshot for oprun evidence trail (Agent-072)."""
    timestamp: str
    field: list          # serializable 2-D list
    gradient_y: list
    gradient_x: list
    active_nodes: int
    hotspot_count: int   # nodes above 0.8 pressure
    triggered_by: str    # agent_id or 'system'


class GradientFieldRouter:
    """
    Vectorized numpy gradient field router.

    Thread-safe: all field mutations acquire self._lock.
    All callers (scientist agents + special governance agents) share
    the singleton instance exposed at module level as `gfr`.
    """

    def __init__(self, grid_size: int = DEFAULT_GRID_SIZE):
        self.grid_size = grid_size
        self._lock = threading.RLock()
        # φ — potential field, shape (grid_size, grid_size)
        self._field: np.ndarray = np.full(
            (grid_size, grid_size), FLOOR_VALUE, dtype=np.float64
        )
        self._last_snapshot: Optional[GFRSnapshot] = None

    # ------------------------------------------------------------------
    # Field mutation
    # ------------------------------------------------------------------

    def update_field_node(
        self,
        row: int,
        col: int,
        cpu_load: float,
        queue_depth: float,
        triggered_by: str = "system",
    ) -> None:
        """
        Update a single node's pressure from scientist telemetry.

        Called by Agent-063 through Agent-067 after each measurement cycle.
        """
        pressure = CPU_WEIGHT * cpu_load + QUEUE_WEIGHT * queue_depth
        with self._lock:
            self._field[row, col] = max(FLOOR_VALUE, pressure)

    def update_field_batch(
        self,
        updates: list[dict],
        triggered_by: str = "system",
    ) -> None:
        """
        Batch-update multiple nodes atomically.

        updates: list of {row, col, cpu_load, queue_depth}
        """
        with self._lock:
            for u in updates:
                pressure = CPU_WEIGHT * u["cpu_load"] + QUEUE_WEIGHT * u["queue_depth"]
                self._field[u["row"], u["col"]] = max(FLOOR_VALUE, pressure)

    def reset_field(self) -> None:
        """Reset all nodes to floor pressure."""
        with self._lock:
            self._field[:] = FLOOR_VALUE

    # ------------------------------------------------------------------
    # Routing decision
    # ------------------------------------------------------------------

    def route(self, origin_row: int, origin_col: int) -> tuple[int, int]:
        """
        Given a workload at (origin_row, origin_col), return the
        destination node by following the steepest descent of φ.

        Returns (origin_row, origin_col) unchanged if already at
        equilibrium (gradient vanishes — lowest-pressure configuration).
        """
        with self._lock:
            # --- Governance gate: clamp before gradient ---
            safe_field = np.clip(self._field, FLOOR_VALUE, None)

            # --- Boundary-safe vectorized gradient ---
            grad_y, grad_x = np.gradient(safe_field)

            gy = grad_y[origin_row, origin_col]
            gx = grad_x[origin_row, origin_col]
            magnitude = np.sqrt(gy**2 + gx**2)

            # Equilibrium check
            if magnitude < EQUILIBRIUM_THRESHOLD:
                return (origin_row, origin_col)

            # Normalized steepest descent (negative = downhill)
            step_y = -gy / magnitude
            step_x = -gx / magnitude

            dest_row = int(np.clip(
                round(origin_row + step_y), 0, self.grid_size - 1
            ))
            dest_col = int(np.clip(
                round(origin_col + step_x), 0, self.grid_size - 1
            ))

            return (dest_row, dest_col)

    # ------------------------------------------------------------------
    # Evidence snapshot (Agent-072 oprun trail)
    # ------------------------------------------------------------------

    def snapshot(self, triggered_by: str = "system") -> GFRSnapshot:
        """
        Capture the full current field state as an immutable evidence record.
        Used by Agent-072 (Evidence) to write to the oprun trail.
        """
        with self._lock:
            safe_field = np.clip(self._field, FLOOR_VALUE, None)
            grad_y, grad_x = np.gradient(safe_field)
            snap = GFRSnapshot(
                timestamp=datetime.now(timezone.utc).isoformat(),
                field=safe_field.tolist(),
                gradient_y=grad_y.tolist(),
                gradient_x=grad_x.tolist(),
                active_nodes=int(np.sum(self._field > FLOOR_VALUE)),
                hotspot_count=int(np.sum(self._field > 0.8)),
                triggered_by=triggered_by,
            )
            self._last_snapshot = snap
            return snap

    def last_snapshot(self) -> Optional[GFRSnapshot]:
        """Return the most recent snapshot without recomputing."""
        return self._last_snapshot

    # ------------------------------------------------------------------
    # Status / introspection
    # ------------------------------------------------------------------

    def status(self) -> dict:
        """Lightweight health summary for Neural Orchestrator (Agent-129)."""
        with self._lock:
            safe_field = np.clip(self._field, FLOOR_VALUE, None)
            return {
                "grid_size": self.grid_size,
                "mean_pressure": float(np.mean(safe_field)),
                "max_pressure": float(np.max(safe_field)),
                "min_pressure": float(np.min(safe_field)),
                "hotspot_count": int(np.sum(safe_field > 0.8)),
                "active_nodes": int(np.sum(safe_field > FLOOR_VALUE)),
                "equilibrium": bool(np.max(safe_field) - np.min(safe_field) < EQUILIBRIUM_THRESHOLD),
            }


# --- Module-level singleton ---
# All agents import and use this instance directly.
gfr = GradientFieldRouter()
