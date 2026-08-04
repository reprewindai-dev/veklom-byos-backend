"""
Capability Debouncer
Collects rapid requirement changes and emits stabilized requirements

Purpose:
- User types quickly (generating graph changes rapidly)
- Debouncer waits for settling window (200-500ms)
- Merges duplicate requirements
- Emits stable batch to queue

This prevents 20 builds for slightly different versions of the same requirement.

Location: veklom-byos-backend/backend/gpc/poltergeist/debouncer.py
"""

import asyncio
from typing import Dict, List, Optional, Callable, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from backend.gpc.poltergeist.watcher import CapabilityRequirement


@dataclass
class DebouncedRequirement:
    """A settled, deduplicated requirement ready for queue"""
    capability_id: str
    requirement: CapabilityRequirement
    duplicate_count: int = 1  # How many times this was requested
    first_seen_at: datetime = field(default_factory=datetime.utcnow)
    last_seen_at: datetime = field(default_factory=datetime.utcnow)


class CapabilityDebouncer:
    """
    Debounces capability requirements.
    
    Workflow:
    1. Receive rapid requirement events
    2. Collect in pending buffer
    3. Wait for settling window (no new events)
    4. Merge duplicates
    5. Emit to queue
    
    Example:
    - User types fast, graph changes 50 times in 100ms
    - Debouncer collects all 50 changes
    - Groups by fingerprint (20 unique requirements)
    - Emits 20 to queue after 200ms silence
    """
    
    def __init__(
        self,
        on_settled: Callable[[List[DebouncedRequirement]], None],
        settle_delay_ms: int = 200,
    ):
        """
        Initialize debouncer.
        
        Args:
            on_settled: Callback when requirements settle
            settle_delay_ms: Wait this long before emitting
        """
        self.on_settled = on_settled
        self.settle_delay_ms = settle_delay_ms
        
        # State
        self._pending: Dict[str, CapabilityRequirement] = {}  # capability_id -> requirement
        self._counts: Dict[str, int] = {}  # capability_id -> count
        self._seen_at: Dict[str, datetime] = {}  # capability_id -> timestamp
        self._settle_task: Optional[asyncio.Task] = None
        self._pipeline_id: Optional[str] = None
    
    async def add_requirement(self, requirement: CapabilityRequirement) -> None:
        """
        Add a requirement to the debouncer.
        
        If this is a duplicate (same fingerprint), increment count.
        Otherwise, add as new.
        
        Args:
            requirement: The requirement to add
        """
        cap_id = requirement.capability_id
        
        # Track duplicate
        if cap_id in self._pending:
            self._counts[cap_id] += 1
        else:
            self._pending[cap_id] = requirement
            self._counts[cap_id] = 1
        
        # Update last seen time
        self._seen_at[cap_id] = datetime.utcnow()
        
        # Track which pipeline (for grouping)
        if not self._pipeline_id:
            self._pipeline_id = requirement.pipeline_id
        
        # Cancel existing settle task
        if self._settle_task:
            self._settle_task.cancel()
        
        # Schedule new settle
        self._settle_task = asyncio.create_task(self._settle())
    
    async def _settle(self) -> None:
        """
        Wait for settling window, then emit.
        
        If no new events arrive within settle_delay_ms,
        emit all pending requirements.
        """
        try:
            # Wait for settling window
            await asyncio.sleep(self.settle_delay_ms / 1000)
            
            # Check if any new events arrived (shouldn't happen)
            # If they did, _settle() would have been cancelled and rescheduled
            
            # Build settled list
            settled: List[DebouncedRequirement] = []
            
            for cap_id, requirement in self._pending.items():
                count = self._counts[cap_id]
                
                settled.append(DebouncedRequirement(
                    capability_id=cap_id,
                    requirement=requirement,
                    duplicate_count=count,
                    first_seen_at=self._seen_at[cap_id],
                    last_seen_at=self._seen_at[cap_id],
                ))
            
            # Emit
            if settled:
                await self._emit_settled(settled)
            
            # Reset
            self._reset()
        
        except asyncio.CancelledError:
            # Task was cancelled (new events arrived), that's ok
            pass
    
    async def _emit_settled(self, settled: List[DebouncedRequirement]) -> None:
        """
        Emit settled requirements.
        
        Args:
            settled: List of settled requirements
        """
        print(
            f"[Debouncer] Emitting {len(settled)} settled requirements "
            f"(pipeline {self._pipeline_id})"
        )
        
        for req in settled:
            if req.duplicate_count > 1:
                print(
                    f"  [{req.capability_id}] "
                    f"(requested {req.duplicate_count} times)"
                )
            else:
                print(f"  [{req.capability_id}]")
        
        # Call callback
        if asyncio.iscoroutinefunction(self.on_settled):
            await self.on_settled(settled)
        else:
            self.on_settled(settled)
    
    def _reset(self) -> None:
        """Reset debouncer state"""
        self._pending.clear()
        self._counts.clear()
        self._seen_at.clear()
        self._pipeline_id = None
        self._settle_task = None
    
    def cancel(self) -> None:
        """Cancel any pending settle"""
        if self._settle_task:
            self._settle_task.cancel()
        self._reset()


class MultiPipelineDebouncer:
    """
    Manages debouncers per pipeline.
    
    Each pipeline has its own debouncer to avoid cross-pipeline
    interference.
    """
    
    def __init__(
        self,
        on_settled: Callable[[str, List[DebouncedRequirement]], None],
        settle_delay_ms: int = 200,
    ):
        """
        Initialize multi-pipeline debouncer.
        
        Args:
            on_settled: Callback(pipeline_id, settled_requirements)
            settle_delay_ms: Settling window per debouncer
        """
        self.on_settled = on_settled
        self.settle_delay_ms = settle_delay_ms
        
        # Per-pipeline debouncers
        self._debouncers: Dict[str, CapabilityDebouncer] = {}
    
    async def add_requirement(self, requirement: CapabilityRequirement) -> None:
        """
        Add requirement to appropriate pipeline debouncer.
        
        Args:
            requirement: The requirement
        """
        pipeline_id = requirement.pipeline_id
        
        # Create debouncer if needed
        if pipeline_id not in self._debouncers:
            async def on_settled(settled):
                await self.on_settled(pipeline_id, settled)
            
            self._debouncers[pipeline_id] = CapabilityDebouncer(
                on_settled=on_settled,
                settle_delay_ms=self.settle_delay_ms,
            )
        
        # Add to pipeline's debouncer
        debouncer = self._debouncers[pipeline_id]
        await debouncer.add_requirement(requirement)
    
    def cancel_pipeline(self, pipeline_id: str) -> None:
        """Cancel debouncer for a pipeline"""
        if pipeline_id in self._debouncers:
            self._debouncers[pipeline_id].cancel()
            del self._debouncers[pipeline_id]
    
    def cancel_all(self) -> None:
        """Cancel all debouncers"""
        for debouncer in self._debouncers.values():
            debouncer.cancel()
        self._debouncers.clear()


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

"""
from backend.gpc.poltergeist.debouncer import MultiPipelineDebouncer

# Callback when requirements settle
async def on_settled(pipeline_id: str, settled: List[DebouncedRequirement]):
    print(f"Pipeline {pipeline_id}: {len(settled)} requirements settled")
    for req in settled:
        if req.duplicate_count > 1:
            print(f"  {req.capability_id} (x{req.duplicate_count})")
        else:
            print(f"  {req.capability_id}")
    
    # Enqueue to build queue
    for req in settled:
        await build_queue.enqueue(req.requirement, priority=req.requirement.priority)

# Create multi-pipeline debouncer
debouncer = MultiPipelineDebouncer(
    on_settled=on_settled,
    settle_delay_ms=200
)

# In watcher, when requirement detected:
await debouncer.add_requirement(requirement)

# Results in:
# [Debouncer] User types fast, 50 graph changes in 100ms
# [Debouncer] Collects all changes, groups by fingerprint
# [Debouncer] Waits 200ms for settling
# [Debouncer] Emitting 20 settled requirements
#   [looker_connector] (requested 10 times)
#   [postgres_adapter] (requested 5 times)
#   [transform_service] (requested 5 times)
# Queuing 20 requirements to build queue...
"""
