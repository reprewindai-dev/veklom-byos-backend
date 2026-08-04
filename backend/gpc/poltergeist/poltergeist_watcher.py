"""
Poltergeist Watcher Service
Watches GPC graph changes and emits capability requirements to the queue

Purpose:
- Subscribe to GPC graph formation stream
- Detect capability requirements in real-time
- Emit to debouncer for settling
- Handle requirement merging and prioritization

Location: veklom-byos-backend/backend/gpc/poltergeist/watcher.py
"""

import asyncio
import hashlib
import json
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, Dict, Set, List, Callable
from enum import Enum

from pydantic import BaseModel


class CapabilityRequirementType(str, Enum):
    """Type of capability being required"""
    CONNECTOR = "connector"  # External API/database connector
    TRANSFORM = "transform"  # Data transformation
    VALIDATOR = "validator"  # Data validation
    AGGREGATOR = "aggregator"  # Aggregation function
    AI_MODEL = "ai_model"  # LLM or ML model
    POLICY_MODULE = "policy_module"  # Policy/governance module
    AGENT_TOOL = "agent_tool"  # Tool for autonomous agent
    OUTPUT = "output"  # Output handler (database, storage, webhook)


@dataclass
class CapabilityRequirement:
    """A requirement for a capability (node)"""
    capability_id: str  # Deterministic hash
    requirement_type: CapabilityRequirementType
    node_type: str  # e.g., "looker_connector"
    external_system: Optional[str]  # e.g., "looker", "postgres", "openai"
    operations: List[str]  # e.g., ["query_dimensions", "list_models"]
    input_ports: List[str]  # Expected input types
    output_ports: List[str]  # Expected output types
    data_residency_region: str  # "ca-central-1", "on-premise", etc.
    tenant_id: str
    pipeline_id: str
    graph_revision: int  # Which graph iteration produced this
    requested_at: datetime
    priority: int = 50  # 0-100, higher = more important

    def to_dict(self) -> Dict:
        """Convert to dict for JSON serialization"""
        return {
            **asdict(self),
            "requirement_type": self.requirement_type.value,
            "requested_at": self.requested_at.isoformat(),
        }


class CapabilityWatcher:
    """
    Watches a stream of GPC graph changes and emits capability requirements.

    Workflow:
    1. Receive graph change events
    2. Detect new or modified nodes
    3. Fingerprint each requirement
    4. Emit to debouncer
    """

    def __init__(
        self,
        on_requirement: Callable[[CapabilityRequirement], None],
        settle_delay_ms: int = 200
    ):
        """
        Args:
            on_requirement: Callback when requirement is detected
            settle_delay_ms: Wait this long before emitting after last change
        """
        self.on_requirement = on_requirement
        self.settle_delay_ms = settle_delay_ms

        # State tracking
        self._pending_changes: Dict[str, dict] = {}  # node_id -> change
        self._known_requirements: Set[str] = set()  # Known fingerprints
        self._settle_tasks: Dict[str, asyncio.Task] = {}  # Settle timers per pipeline
        self._last_change_time: Dict[str, datetime] = {}  # Track timing

    async def on_graph_change(
        self,
        tenant_id: str,
        pipeline_id: str,
        graph_revision: int,
        nodes: List[Dict],
        edges: List[Dict]
    ):
        """
        Called when the GPC graph changes.

        Args:
            tenant_id: Tenant context
            pipeline_id: Which pipeline changed
            graph_revision: Version number of this graph
            nodes: Current nodes
            edges: Current edges
        """
        # Cancel existing settle timer for this pipeline
        settle_key = f"{pipeline_id}:settle"
        if settle_key in self._settle_tasks:
            self._settle_tasks[settle_key].cancel()

        # Detect capability requirements
        requirements: List[CapabilityRequirement] = []

        for node in nodes:
            req = self._detect_requirement(
                tenant_id=tenant_id,
                pipeline_id=pipeline_id,
                graph_revision=graph_revision,
                node=node,
                all_nodes=nodes,
                edges=edges
            )

            if req and req.capability_id not in self._known_requirements:
                requirements.append(req)
                self._known_requirements.add(req.capability_id)

        # Schedule settle
        if requirements:
            self._last_change_time[pipeline_id] = datetime.utcnow()

            # Defer settle until no changes arrive for settle_delay_ms
            async def settle():
                await asyncio.sleep(self.settle_delay_ms / 1000)

                # Emit all requirements
                for req in requirements:
                    await self._emit_requirement(req)

            task = asyncio.create_task(settle())
            self._settle_tasks[settle_key] = task

    def _detect_requirement(
        self,
        tenant_id: str,
        pipeline_id: str,
        graph_revision: int,
        node: Dict,
        all_nodes: List[Dict],
        edges: List[Dict]
    ) -> Optional[CapabilityRequirement]:
        """
        Analyze a node and detect if it requires a capability.
        """
        node_id = node.get("id")
        node_type = node.get("data", {}).get("node_type") or node.get("node_type")

        if not node_type:
            return None

        # Get expected input/output ports
        node_data = node.get("data", {})
        input_ports = node_data.get("input_ports", [])
        output_ports = node_data.get("output_ports", [])

        # Detect requirement type
        req_type, external_system, operations = self._infer_requirement(
            node_type, node_data
        )

        if not req_type:
            return None  # Already built-in capability

        # Calculate deterministic fingerprint
        capability_id = self._fingerprint_requirement(
            node_type, external_system, operations, node_data
        )

        # Calculate priority (critical path = higher priority)
        priority = self._calculate_priority(
            node_id, all_nodes, edges, external_system
        )

        return CapabilityRequirement(
            capability_id=capability_id,
            requirement_type=req_type,
            node_type=node_type,
            external_system=external_system,
            operations=operations,
            input_ports=[p.get("name", f"in_{i}") for i, p in enumerate(input_ports)],
            output_ports=[p.get("name", f"out_{i}") for i, p in enumerate(output_ports)],
            data_residency_region=node_data.get("data_residency_region", "ca-central-1"),
            tenant_id=tenant_id,
            pipeline_id=pipeline_id,
            graph_revision=graph_revision,
            requested_at=datetime.utcnow(),
            priority=priority,
        )

    def _infer_requirement(self, node_type: str, node_data: Dict) -> tuple:
        """
        Infer what capability is needed based on node type.

        Returns: (req_type, external_system, operations) or (None, None, None)
        """
        # Connectors
        if node_type.endswith("_connector") or "api" in node_type.lower():
            system = node_data.get("external_system") or node_type.replace("_connector", "")
            ops = node_data.get("operations", ["query", "fetch"])
            return CapabilityRequirementType.CONNECTOR, system, ops

        # Transforms
        if node_type.endswith("_transform") or "transform" in node_type.lower():
            system = node_type.replace("_transform", "")
            ops = ["transform"]
            return CapabilityRequirementType.TRANSFORM, system, ops

        # Models / AI
        if "model" in node_type.lower() or "llm" in node_type.lower():
            model_name = node_data.get("model_name") or node_type
            return CapabilityRequirementType.AI_MODEL, model_name, ["inference"]

        # Custom nodes (usually require manufacture)
        if "custom" in node_type.lower() or node_data.get("is_custom"):
            system = node_data.get("system", node_type)
            return CapabilityRequirementType.CONNECTOR, system, ["query"]

        # Built-in or already known
        return None, None, None

    def _fingerprint_requirement(
        self,
        node_type: str,
        external_system: Optional[str],
        operations: List[str],
        node_data: Dict
    ) -> str:
        """
        Create deterministic fingerprint for this requirement.
        Same inputs always produce same fingerprint.
        """
        # Extract config that affects the capability
        config = {
            "node_type": node_type,
            "external_system": external_system,
            "operations": sorted(operations),
            "version": node_data.get("version", "latest"),
            "schema": node_data.get("output_schema"),  # If output schema is specified
        }

        # Stable JSON
        stable = json.dumps(config, sort_keys=True, default=str)

        # Deterministic hash
        return hashlib.sha256(stable.encode()).hexdigest()[:16]

    def _calculate_priority(
        self,
        node_id: str,
        all_nodes: List[Dict],
        edges: List[Dict],
        external_system: Optional[str]
    ) -> int:
        """
        Prioritize capabilities on critical path.

        Scoring:
        - Early in pipeline (closer to inputs): higher
        - More downstream nodes depend on it: higher
        - External system (riskier to manufacture): higher
        """
        score = 50

        # Calculate in-degree and out-degree
        in_degree = len([e for e in edges if e.get("target") == node_id])
        out_degree = len([e for e in edges if e.get("source") == node_id])

        # High out-degree = many things depend on this
        score += min(out_degree * 5, 20)

        # Early in pipeline (low in-degree) = higher
        if in_degree == 0:
            score += 20

        # External system connectivity = higher risk, higher priority
        if external_system:
            score += 10

        # Cap at 100
        return min(score, 100)

    async def _emit_requirement(self, requirement: CapabilityRequirement):
        """
        Emit the requirement to be processed.
        This will go to the debouncer -> queue -> builder.
        """
        print(
            f"[Watcher] Capability requirement: {requirement.node_type} "
            f"(priority={requirement.priority})"
        )

        # Async call to callback
        if asyncio.iscoroutinefunction(self.on_requirement):
            await self.on_requirement(requirement)
        else:
            self.on_requirement(requirement)

    def reset(self):
        """Reset watcher state"""
        self._pending_changes.clear()
        self._known_requirements.clear()
        for task in self._settle_tasks.values():
            task.cancel()
        self._settle_tasks.clear()


# ============================================================================
# EXAMPLE USAGE IN FASTAPI ROUTE
# ============================================================================

"""
from fastapi import FastAPI, WebSocket
from fastapi.responses import StreamingResponse

app = FastAPI()

# Shared watcher
watcher: Optional[CapabilityWatcher] = None

async def on_requirement_detected(req: CapabilityRequirement):
    # This gets called when watcher detects a requirement
    # In production, this enqueues it to the Poltergeist build queue
    print(f"Requirement detected: {req.capability_id}")
    await poltergeist_queue.enqueue(req)

@app.on_event("startup")
async def startup():
    global watcher
    watcher = CapabilityWatcher(on_requirement=on_requirement_detected)

@app.post("/api/v1/gpc/generate")
async def generate_from_intent(request: NLToGraphRequest):
    # User asks for intent
    # LLM generates graph with nodes
    # Graph arrives -> send to watcher

    pipeline_graph = await llm_generate(request.user_intent)

    # Notify watcher of new graph
    await watcher.on_graph_change(
        tenant_id=request.tenant_id,
        pipeline_id=pipeline_graph.pipeline_id,
        graph_revision=1,
        nodes=pipeline_graph.nodes,
        edges=pipeline_graph.edges
    )

    # Return to frontend
    return pipeline_graph

@app.websocket("/ws/gpc/live-status")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    try:
        while True:
            # Stream capability build status to frontend
            status = await poltergeist_queue.peek_status()
            await websocket.send_json(status.to_dict())
            await asyncio.sleep(0.5)
    except Exception as e:
        print(f"WebSocket error: {e}")
"""
