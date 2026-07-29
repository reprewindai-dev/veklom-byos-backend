"""
Builder Orchestrator
Manages the build loop and autonomous capability manufacturing

Process:
1. Dequeue from CapabilityBuildQueue
2. Select appropriate builder based on requirement type
3. Run builder.build()
4. Update queue with result
5. Loop continuously

Location: veklom-byos-backend/backend/gpc/poltergeist/orchestrator.py
"""

import asyncio
from typing import Dict, Optional, Any
from datetime import datetime

from backend.gpc.poltergeist.capability_queue import CapabilityBuildQueue, QueueStatus
from backend.gpc.poltergeist.haunt_cache import HauntCachePlane
from backend.gpc.poltergeist.watcher import CapabilityRequirementType
from backend.gpc.builders.base_builder import BaseCapabilityBuilder
from backend.gpc.builders.openapi_builder import OpenAPIConnectorBuilder
from backend.gpc.builders.graphql_builder import GraphQLConnectorBuilder
from backend.gpc.builders.python_builder import PythonTransformBuilder
from backend.gpc.builders.database_builder import DatabaseAdapterBuilder


class BuilderOrchestrator:
    """
    Orchestrates autonomous capability building.
    
    Manages:
    1. Builder factory (select builder for requirement)
    2. Build loop (continuous dequeue → build → complete)
    3. Heartbeat tracking (detect crashes)
    4. Error handling and retries
    5. Progress reporting via callbacks
    """
    
    def __init__(
        self,
        queue: CapabilityBuildQueue,
        cache: HauntCachePlane,
        max_concurrent_builders: int = 5,
        pgl_client=None,
        repogate_client=None,
    ):
        """
        Initialize orchestrator.
        
        Args:
            queue: Capability build queue
            cache: Haunt cache plane
            max_concurrent_builders: Max parallel builds
            pgl_client: Gnomledger client (optional)
            repogate_client: Security scanner client (optional)
        """
        self.queue = queue
        self.cache = cache
        self.max_concurrent_builders = max_concurrent_builders
        self.pgl_client = pgl_client
        self.repogate_client = repogate_client
        
        # Registry of builders
        self.builders: Dict[CapabilityRequirementType, type] = {
            CapabilityRequirementType.CONNECTOR: OpenAPIConnectorBuilder,
            CapabilityRequirementType.TRANSFORM: PythonTransformBuilder,
            CapabilityRequirementType.DATABASE: DatabaseAdapterBuilder,
            CapabilityRequirementType.AGENT: None,  # Special handling
        }
        
        # Active tasks
        self._active_tasks: Dict[str, asyncio.Task] = {}
        self._running = False
    
    def register_builder(
        self,
        requirement_type: CapabilityRequirementType,
        builder_class: type,
    ) -> None:
        """
        Register a builder for a requirement type.
        
        Args:
            requirement_type: The requirement type to handle
            builder_class: The builder class (must inherit BaseCapabilityBuilder)
        """
        self.builders[requirement_type] = builder_class
    
    async def start(self) -> None:
        """
        Start the build loop.
        
        Runs until stop() is called.
        Continuously dequeues and builds capabilities.
        """
        self._running = True
        
        print(f"[Orchestrator] Starting with max {self.max_concurrent_builders} concurrent builders")
        
        try:
            while self._running:
                # Check how many builders are active
                active_count = len(self._active_tasks)
                
                if active_count < self.max_concurrent_builders:
                    # Try to dequeue
                    queued = await self.queue.dequeue_next()
                    
                    if queued:
                        print(
                            f"[Orchestrator] Dequeued {queued.capability_id} "
                            f"(priority={queued.priority})"
                        )
                        
                        # Start build task
                        task = asyncio.create_task(
                            self._build_capability(queued)
                        )
                        
                        self._active_tasks[queued.queue_id] = task
                    else:
                        # Queue empty, wait a bit
                        await asyncio.sleep(1.0)
                else:
                    # At capacity, wait for task to complete
                    done, _ = await asyncio.wait(
                        self._active_tasks.values(),
                        timeout=1.0,
                        return_when=asyncio.FIRST_COMPLETED,
                    )
                    
                    # Remove completed tasks
                    for task in done:
                        for queue_id, t in list(self._active_tasks.items()):
                            if t is task:
                                del self._active_tasks[queue_id]
                                break
        
        except Exception as e:
            print(f"[Orchestrator] Error: {e}")
        
        finally:
            self._running = False
            print("[Orchestrator] Build loop stopped")
    
    async def stop(self) -> None:
        """Stop the build loop"""
        self._running = False
        
        # Wait for active tasks to complete
        if self._active_tasks:
            await asyncio.gather(*self._active_tasks.values(), return_exceptions=True)
    
    async def _build_capability(self, queued) -> None:
        """
        Build a single capability.
        
        Args:
            queued: QueuedCapability to build
        """
        queue_id = queued.queue_id
        capability_id = queued.capability_id
        requirement = queued.requirement
        
        try:
            # Select builder
            builder = await self._select_builder(requirement)
            
            if not builder:
                await self.queue.mark_complete(
                    queue_id,
                    success=False,
                    error_message=f"No builder for {requirement.requirement_type}",
                )
                return
            
            # Build with status callback
            async def on_status(status, message):
                print(f"[Builder {capability_id}] {status.value}: {message}")
            
            print(f"[Builder {capability_id}] Starting build...")
            result = await builder.build(requirement, on_status=on_status)
            
            if result.success:
                print(
                    f"[Builder {capability_id}] ✅ Success in {result.duration_seconds:.1f}s"
                )
                await self.queue.mark_complete(queue_id, success=True)
            else:
                print(
                    f"[Builder {capability_id}] ❌ Failed: {result.error_message}"
                )
                await self.queue.mark_complete(
                    queue_id,
                    success=False,
                    error_message=result.error_message,
                )
        
        except Exception as e:
            print(f"[Builder {capability_id}] Exception: {str(e)}")
            await self.queue.mark_complete(
                queue_id,
                success=False,
                error_message=str(e),
            )
    
    async def _select_builder(
        self,
        requirement,
    ) -> Optional[BaseCapabilityBuilder]:
        """
        Select appropriate builder for requirement.
        
        Args:
            requirement: The capability requirement
            
        Returns:
            Instantiated builder, or None if no match
        """
        req_type = requirement.requirement_type
        builder_class = self.builders.get(req_type)
        
        if not builder_class:
            return None
        
        # Instantiate builder
        builder = builder_class(
            cache=self.cache,
            pgl_client=self.pgl_client,
            repogate_client=self.repogate_client,
        )
        
        return builder
    
    async def get_orchestrator_status(self) -> Dict[str, Any]:
        """
        Get orchestrator status.
        
        Returns:
            Status dict with active tasks, queue status, etc.
        """
        queue_status = await self.queue.get_queue_status()
        
        return {
            "running": self._running,
            "active_builders": len(self._active_tasks),
            "max_concurrent": self.max_concurrent_builders,
            "queue": queue_status,
            "timestamp": datetime.utcnow().isoformat(),
        }


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

"""
from backend.gpc.poltergeist.orchestrator import BuilderOrchestrator
from backend.gpc.poltergeist.capability_queue import CapabilityBuildQueue
from backend.gpc.poltergeist.haunt_cache import HauntCachePlane

# Initialize components
cache = HauntCachePlane(redis_url="redis://localhost:6379")
queue = CapabilityBuildQueue(redis_url="redis://localhost:6379")

# Create orchestrator
orchestrator = BuilderOrchestrator(
    queue=queue,
    cache=cache,
    max_concurrent_builders=5,
)

# Run build loop in background
build_task = asyncio.create_task(orchestrator.start())

# Enqueue a capability
requirement = CapabilityRequirement(
    capability_id="looker_connector_v1",
    requirement_type=CapabilityRequirementType.CONNECTOR,
    node_type="looker_connector",
    external_system="looker",
    operations=["list_models", "query_dimensions"],
    input_ports=["config"],
    output_ports=["data"],
    data_residency_region="ca-central-1",
    tenant_id="default",
    pipeline_id="pipeline_123",
    graph_revision=1,
    requested_at=datetime.utcnow(),
)

enqueued = await queue.enqueue(requirement)

if enqueued:
    print("Queued for building")
    
    # Wait for build to complete (polling)
    while True:
        status = await orchestrator.get_orchestrator_status()
        print(f"Active builders: {status['active_builders']}")
        
        # Check if our capability is done
        queue_status = status['queue']
        if queue_status.get('built') and queue_status.get('pending') == 0:
            break
        
        await asyncio.sleep(1)
    
    print("Build complete!")

# Stop orchestrator
await orchestrator.stop()
"""
