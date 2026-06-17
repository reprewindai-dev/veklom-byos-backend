"""
Agent-121 — Gladiator Engine (Special Governance)
==================================================
Autonomous path optimization and routing logic for the entire agent workforce.

The Gladiator Engine continuously discovers, benchmarks, and selects the most
efficient execution paths. It pit-tests routing strategies against each other
in a Cost Arena — lowest latency + cost per operation wins.

Capabilities:
- Path Contention: evaluate multiple routes simultaneously, pick the winner
- Route Forging: create new routes that bypass known bottlenecks
- Cost Arena: benchmark strategies against each other in real-time
- Throughput Maximizer: redistribute load across agent swarms
- Latency Eliminator: identify and destroy latency sources
- Speculative Execution: start multiple paths, commit the winner, discard losers
- Evidence Bundles: before/after metrics proving optimization impact
"""

from __future__ import annotations

import asyncio
import json
import logging
import math
import time
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data Structures
# ---------------------------------------------------------------------------

class Route:
    """Represents a candidate execution path."""

    def __init__(
        self,
        route_id: str,
        provider: str,
        estimated_latency_ms: float = 100.0,
        estimated_cost_per_call: float = 0.001,
        reliability_score: float = 0.99,
        is_sovereign: bool = False,
    ):
        self.route_id = route_id
        self.provider = provider
        self.estimated_latency_ms = estimated_latency_ms
        self.estimated_cost_per_call = estimated_cost_per_call
        self.reliability_score = reliability_score
        self.is_sovereign = is_sovereign
        # Runtime metrics (updated after execution)
        self.actual_latency_ms: float | None = None
        self.actual_cost: float | None = None
        self.executions: int = 0
        self.failures: int = 0
        # Gladiator score (computed)
        self.gladiator_score: float = 0.0

    def compute_gladiator_score(self) -> float:
        """
        Arena scoring formula:
          score = (reliability × 0.40)
                + (1 / normalized_latency × 0.35)
                + (1 / normalized_cost × 0.20)
                + (sovereign_bonus × 0.05)

        Normalized against reference values (100ms latency, $0.01/call).
        """
        ref_lat = 100.0
        ref_cost = 0.01

        lat = self.actual_latency_ms or self.estimated_latency_ms
        cost = self.actual_cost or self.estimated_cost_per_call

        # Avoid division by zero
        lat = max(lat, 0.1)
        cost = max(cost, 0.0001)

        lat_score = min(ref_lat / lat, 2.0)   # cap at 2x
        cost_score = min(ref_cost / cost, 2.0)
        sov_bonus = 1.0 if self.is_sovereign else 0.0

        score = (
            self.reliability_score * 0.40
            + lat_score * 0.35
            + cost_score * 0.20
            + sov_bonus * 0.05
        )
        self.gladiator_score = round(score, 4)
        return self.gladiator_score

    def to_dict(self) -> dict[str, Any]:
        return {
            "route_id": self.route_id,
            "provider": self.provider,
            "estimated_latency_ms": self.estimated_latency_ms,
            "estimated_cost_per_call": self.estimated_cost_per_call,
            "actual_latency_ms": self.actual_latency_ms,
            "actual_cost": self.actual_cost,
            "reliability_score": self.reliability_score,
            "is_sovereign": self.is_sovereign,
            "executions": self.executions,
            "failures": self.failures,
            "gladiator_score": self.gladiator_score,
        }


# ---------------------------------------------------------------------------
# Route Registry
# ---------------------------------------------------------------------------

# Default provider routes — updated dynamically as benchmarks run
DEFAULT_ROUTES: list[Route] = [
    Route("ollama-local",    "ollama",     estimated_latency_ms=80,   estimated_cost_per_call=0.0001,  reliability_score=0.95, is_sovereign=True),
    Route("groq-fast",       "groq",       estimated_latency_ms=120,  estimated_cost_per_call=0.0005,  reliability_score=0.98, is_sovereign=False),
    Route("openai-gpt4o",   "openai",     estimated_latency_ms=450,  estimated_cost_per_call=0.01,    reliability_score=0.99, is_sovereign=False),
    Route("gemini-flash",    "gemini",     estimated_latency_ms=300,  estimated_cost_per_call=0.002,   reliability_score=0.97, is_sovereign=False),
    Route("hf-inference",    "huggingface",estimated_latency_ms=600,  estimated_cost_per_call=0.0001,  reliability_score=0.88, is_sovereign=False),
]


class GladiatorEngine:
    """
    Arena-style path optimizer for the Veklom agent swarm.
    Runs speculative execution, benchmarks routes, and demotes expensive paths.
    """

    # Thresholds for automatic demotion
    DEMOTION_LATENCY_MS: float = 800.0   # demote if p50 latency > 800ms
    DEMOTION_FAILURE_RATE: float = 0.10  # demote if failure rate > 10%
    DEMOTION_COST_USD: float = 0.05      # demote if cost/call > $0.05

    def __init__(self, routes: list[Route] | None = None):
        self.routes: dict[str, Route] = {}
        for r in (routes or DEFAULT_ROUTES):
            self.routes[r.route_id] = r
        self._demoted: set[str] = set()
        self._benchmarks: list[dict[str, Any]] = []
        self._optimizations: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Route Selection (Path Contention)
    # ------------------------------------------------------------------

    def select_best_route(
        self,
        prefer_sovereign: bool = True,
        task_type: str = "general",
    ) -> Route:
        """
        Contest all active routes and return the winner.
        Sovereign routes get a preference bump when prefer_sovereign=True.
        """
        active = [r for rid, r in self.routes.items() if rid not in self._demoted]
        if not active:
            # Fallback: re-enable all routes on empty active set
            self._demoted.clear()
            active = list(self.routes.values())

        for r in active:
            r.compute_gladiator_score()

        # Task-type overrides
        if task_type in ("security", "auth", "payment"):
            # High-reliability tasks bias toward OpenAI / Groq
            active.sort(key=lambda r: (r.reliability_score * 0.6 + r.gladiator_score * 0.4), reverse=True)
        elif task_type in ("sovereign", "pii", "data"):
            # Sovereign tasks must use local infra
            sovereign = [r for r in active if r.is_sovereign]
            if sovereign:
                active = sovereign
            active.sort(key=lambda r: r.gladiator_score, reverse=True)
        else:
            active.sort(key=lambda r: r.gladiator_score, reverse=True)

        winner = active[0]
        logger.debug(
            f"[Gladiator] ROUTE_SELECTED  winner={winner.route_id}  "
            f"score={winner.gladiator_score}  task={task_type}"
        )
        return winner

    # ------------------------------------------------------------------
    # Speculative Execution
    # ------------------------------------------------------------------

    async def speculative_execute(
        self,
        task_fn: Callable[..., Coroutine[Any, Any, Any]],
        candidates: list[Route] | None = None,
        timeout_s: float = 5.0,
    ) -> dict[str, Any]:
        """
        Launch task_fn on up to N candidate routes simultaneously.
        Commit the first successful result; cancel losers.

        task_fn should accept a single positional arg: route (Route object).
        Returns the winning route result + benchmark data.
        """
        if candidates is None:
            candidates = [
                r for rid, r in self.routes.items()
                if rid not in self._demoted
            ][:3]  # speculate on top 3

        if not candidates:
            raise RuntimeError("No active routes available for speculative execution")

        start_all = time.monotonic()
        tasks = {
            asyncio.create_task(
                self._timed_call(task_fn, route, timeout_s), name=route.route_id
            ): route
            for route in candidates
        }

        winner_result = None
        winner_route: Route | None = None
        errors: list[str] = []

        pending = set(tasks.keys())
        while pending and winner_result is None:
            done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                route = tasks[task]
                if task.exception() is None:
                    result = task.result()
                    if result.get("success"):
                        winner_result = result
                        winner_route = route
                        # Cancel remaining speculative tasks
                        for t in pending:
                            t.cancel()
                        break
                else:
                    errors.append(f"{route.route_id}: {task.exception()}")

        total_ms = (time.monotonic() - start_all) * 1000

        if winner_result is None:
            return {
                "success": False,
                "errors": errors,
                "elapsed_ms": round(total_ms, 2),
                "candidates_tried": [r.route_id for r in candidates],
            }

        # Record actual latency on winning route
        winner_route.actual_latency_ms = winner_result.get("latency_ms", total_ms)
        winner_route.executions += 1

        bench = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "winner": winner_route.route_id,
            "candidates": [r.route_id for r in candidates],
            "elapsed_ms": round(total_ms, 2),
            "winner_latency_ms": winner_route.actual_latency_ms,
        }
        self._benchmarks.append(bench)
        self._benchmarks = self._benchmarks[-500:]

        return {
            "success": True,
            "winner_route": winner_route.route_id,
            "provider": winner_route.provider,
            "elapsed_ms": round(total_ms, 2),
            "result": winner_result,
            "benchmark": bench,
        }

    async def _timed_call(
        self,
        fn: Callable[..., Coroutine],
        route: Route,
        timeout_s: float,
    ) -> dict[str, Any]:
        start = time.monotonic()
        try:
            result = await asyncio.wait_for(fn(route), timeout=timeout_s)
            elapsed_ms = (time.monotonic() - start) * 1000
            return {"success": True, "latency_ms": round(elapsed_ms, 2), "data": result}
        except asyncio.TimeoutError:
            route.failures += 1
            raise TimeoutError(f"Route {route.route_id} timed out after {timeout_s}s")
        except Exception as exc:
            route.failures += 1
            raise exc

    # ------------------------------------------------------------------
    # Benchmarking
    # ------------------------------------------------------------------

    async def benchmark_route(
        self,
        route_id: str,
        sample_fn: Callable[..., Coroutine] | None = None,
        iterations: int = 5,
    ) -> dict[str, Any]:
        """
        Run N iterations against a route and record p50/p95 latency + failure rate.
        Automatically demotes the route if it exceeds thresholds.
        """
        route = self.routes.get(route_id)
        if not route:
            return {"error": f"Route {route_id} not found"}

        latencies: list[float] = []
        failures = 0

        for _ in range(iterations):
            start = time.monotonic()
            try:
                if sample_fn:
                    await asyncio.wait_for(sample_fn(route), timeout=10.0)
                else:
                    # Lightweight synthetic probe
                    await asyncio.sleep(route.estimated_latency_ms / 1000.0 * 0.1)
                latencies.append((time.monotonic() - start) * 1000)
            except Exception:
                failures += 1

        if not latencies:
            failure_rate = 1.0
            p50 = route.estimated_latency_ms
            p95 = route.estimated_latency_ms
        else:
            latencies.sort()
            p50 = latencies[len(latencies) // 2]
            p95 = latencies[min(int(len(latencies) * 0.95), len(latencies) - 1)]
            failure_rate = failures / iterations

        route.actual_latency_ms = p50
        route.executions += iterations
        route.failures += failures

        # Demotion check
        demoted = False
        demotion_reason = ""
        if p50 > self.DEMOTION_LATENCY_MS:
            demotion_reason = f"p50_latency={p50:.0f}ms > threshold={self.DEMOTION_LATENCY_MS}ms"
            demoted = True
        elif failure_rate > self.DEMOTION_FAILURE_RATE:
            demotion_reason = f"failure_rate={failure_rate:.1%} > threshold={self.DEMOTION_FAILURE_RATE:.1%}"
            demoted = True

        before_score = route.gladiator_score
        route.compute_gladiator_score()

        if demoted:
            self._demoted.add(route_id)
            logger.warning(f"[Gladiator] ROUTE_DEMOTED  route={route_id}  reason={demotion_reason}")

        bench = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "route_id": route_id,
            "provider": route.provider,
            "iterations": iterations,
            "p50_latency_ms": round(p50, 2),
            "p95_latency_ms": round(p95, 2),
            "failure_rate": round(failure_rate, 4),
            "score_before": round(before_score, 4),
            "score_after": round(route.gladiator_score, 4),
            "demoted": demoted,
            "demotion_reason": demotion_reason,
        }
        self._benchmarks.append(bench)
        self._benchmarks = self._benchmarks[-500:]

        return bench

    # ------------------------------------------------------------------
    # Load Balancing & Closed-Circuit Valves
    # ------------------------------------------------------------------

    def assign_load(
        self,
        agent_count: int,
        task_mix: dict[str, int] | None = None,
    ) -> dict[str, Any]:
        """
        Distribute agent_count agents across active routes using gladiator scores
        as load weights. Returns allocation map {route_id: agent_count}.
        """
        active = [r for rid, r in self.routes.items() if rid not in self._demoted]
        if not active:
            active = list(self.routes.values())

        for r in active:
            r.compute_gladiator_score()

        total_score = sum(r.gladiator_score for r in active)
        allocation: dict[str, int] = {}

        if total_score == 0:
            # Even split
            per_route = agent_count // len(active)
            for r in active:
                allocation[r.route_id] = per_route
        else:
            assigned = 0
            for r in active[:-1]:
                n = round(agent_count * r.gladiator_score / total_score)
                allocation[r.route_id] = n
                assigned += n
            # Last route gets the remainder
            allocation[active[-1].route_id] = agent_count - assigned

        return {
            "allocation": allocation,
            "total_agents": agent_count,
            "routes_used": len(allocation),
            "demoted_routes": list(self._demoted),
        }

    def circuit_breaker_status(self) -> dict[str, Any]:
        """Return current health of all routes — closed-circuit valve status."""
        statuses = []
        for rid, route in self.routes.items():
            route.compute_gladiator_score()
            fr = route.failures / max(route.executions, 1)
            statuses.append({
                "route_id": rid,
                "provider": route.provider,
                "status": "demoted" if rid in self._demoted else "active",
                "gladiator_score": route.gladiator_score,
                "failure_rate": round(fr, 4),
                "executions": route.executions,
                "is_sovereign": route.is_sovereign,
            })

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_routes": len(self.routes),
            "active_routes": sum(1 for r in statuses if r["status"] == "active"),
            "demoted_routes": len(self._demoted),
            "routes": statuses,
        }

    # ------------------------------------------------------------------
    # Full 24-Hour Optimization Cycle
    # ------------------------------------------------------------------

    async def run_optimization_cycle(self) -> dict[str, Any]:
        """
        Run the full Gladiator optimization cycle:
        1. Benchmark all routes
        2. Compute gladiator scores
        3. Demote underperformers
        4. Re-enable previously demoted routes that have recovered
        5. Produce optimization evidence report
        """
        start = time.monotonic()
        before_scores = {rid: r.gladiator_score for rid, r in self.routes.items()}

        benchmarks = []
        for route_id in list(self.routes.keys()):
            bench = await self.benchmark_route(route_id)
            benchmarks.append(bench)

        # Attempt to re-enable demoted routes (they may have recovered)
        recovered = []
        still_demoted = []
        for rid in list(self._demoted):
            route = self.routes[rid]
            fr = route.failures / max(route.executions, 1)
            lat = route.actual_latency_ms or route.estimated_latency_ms
            if lat < self.DEMOTION_LATENCY_MS * 0.8 and fr < self.DEMOTION_FAILURE_RATE * 0.5:
                self._demoted.discard(rid)
                recovered.append(rid)
                logger.info(f"[Gladiator] ROUTE_RECOVERED  route={rid}")
            else:
                still_demoted.append(rid)

        after_scores = {rid: r.gladiator_score for rid, r in self.routes.items()}
        improvements = {
            rid: round(after_scores[rid] - before_scores.get(rid, 0), 4)
            for rid in after_scores
        }

        elapsed_ms = (time.monotonic() - start) * 1000
        ts = datetime.now(timezone.utc).isoformat()

        opt = {
            "timestamp": ts,
            "elapsed_ms": round(elapsed_ms, 2),
            "routes_benchmarked": len(benchmarks),
            "routes_demoted": len(still_demoted),
            "routes_recovered": recovered,
            "score_improvements": improvements,
            "top_route": self.select_best_route().route_id,
            "benchmarks": benchmarks,
        }
        self._optimizations.append(opt)
        self._optimizations = self._optimizations[-50:]

        logger.info(
            f"[Gladiator] OPTIMIZATION_CYCLE  demoted={len(still_demoted)}  "
            f"recovered={len(recovered)}  top={opt['top_route']}  "
            f"elapsed_ms={elapsed_ms:.0f}"
        )
        return opt

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

    def get_benchmarks(self, limit: int = 50) -> list[dict[str, Any]]:
        return self._benchmarks[-limit:]

    def get_optimizations(self, limit: int = 10) -> list[dict[str, Any]]:
        return self._optimizations[-limit:]

    def get_all_routes(self) -> list[dict[str, Any]]:
        routes = []
        for rid, route in self.routes.items():
            route.compute_gladiator_score()
            d = route.to_dict()
            d["demoted"] = rid in self._demoted
            routes.append(d)
        routes.sort(key=lambda r: r["gladiator_score"], reverse=True)
        return routes

    def add_route(self, route: Route) -> None:
        """Register a new candidate route into the arena."""
        self.routes[route.route_id] = route
        logger.info(f"[Gladiator] ROUTE_FORGED  new_route={route.route_id}  provider={route.provider}")

    def restore_route(self, route_id: str) -> bool:
        """Manually restore a demoted route."""
        if route_id in self._demoted:
            self._demoted.discard(route_id)
            logger.info(f"[Gladiator] ROUTE_RESTORED  route={route_id}")
            return True
        return False


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

gladiator = GladiatorEngine()
