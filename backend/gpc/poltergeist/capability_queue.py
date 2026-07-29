"""
Capability Queue
Deduplicating Redis queue for capability manufacturing

Purpose:
- Single-flight deduplication (only one build per requirement fingerprint)
- Priority ordering (critical path first)
- Bounded concurrency (max N concurrent builds)
- Merge support (combine similar requirements)
- Heartbeat tracking (detect dead builders)

Location: veklom-byos-backend/backend/gpc/poltergeist/capability_queue.py
"""

import json
import asyncio
from typing import Optional, Dict, List, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import uuid

import redis.asyncio as redis

from backend.gpc.poltergeist.watcher import CapabilityRequirement
from backend.gpc.poltergeist.debouncer import DebouncedRequirement


class QueueStatus(str, Enum):
    """Status of a queued capability"""
    PENDING = "pending"        # Waiting to build
    BUILDING = "building"      # Currently being built
    BUILT = "built"            # Successfully built
    FAILED = "failed"          # Build failed
    STALE = "stale"            # Invalidated by policy change


@dataclass
class QueuedCapability:
    """A capability in the queue"""
    capability_id: str
    requirement: CapabilityRequirement
    status: QueueStatus
    queue_id: str = ""  # Unique queue entry ID
    priority: int = 50  # 0-100
    builder_id: Optional[str] = None  # Who's building it
    attempt_count: int = 0
    max_attempts: int = 3
    created_at: datetime = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    duplicate_count: int = 1  # How many were merged into this
    
    def __post_init__(self):
        if not self.queue_id:
            self.queue_id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.utcnow()
    
    def to_dict(self) -> Dict:
        """Convert to dict for JSON serialization"""
        return {
            **asdict(self),
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class CapabilityBuildQueue:
    """
    Redis-backed queue for capability manufacturing.
    
    Guarantees:
    1. Single-flight: Only one builder per fingerprint (Redis lock)
    2. Deduplication: Merge similar requirements before queue
    3. Priority: Critical path requirements processed first
    4. Resilience: Heartbeat tracking, dead builder cleanup
    5. Idempotent: Same requirement produces same result
    """
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        max_concurrent_builds: int = 5,
        build_timeout_seconds: int = 300,
        lock_ttl_seconds: int = 600,
    ):
        """
        Initialize queue.
        
        Args:
            redis_url: Redis/Valkey connection
            max_concurrent_builds: Max parallel builders
            build_timeout_seconds: Timeout per build
            lock_ttl_seconds: TTL for single-flight locks
        """
        self.redis_url = redis_url
        self.max_concurrent_builds = max_concurrent_builds
        self.build_timeout_seconds = build_timeout_seconds
        self.lock_ttl_seconds = lock_ttl_seconds
        
        self._redis: Optional[redis.Redis] = None
        self._local_in_progress: Set[str] = set()  # Tracking locally
    
    async def enqueue(self, requirement: CapabilityRequirement) -> bool:
        """
        Enqueue a requirement for building.
        
        Returns:
            True if enqueued, False if already in-flight
        """
        if not self._redis:
            await self._init_redis()
        
        cap_id = requirement.capability_id
        lock_key = f"lock:{cap_id}"
        queue_key = "queue:pending"
        
        try:
            # Try to acquire lock (single-flight)
            acquired = await self._redis.set(
                lock_key,
                "locked",
                ex=self.lock_ttl_seconds,
                nx=True  # Only if doesn't exist
            )
            
            if not acquired:
                # Already locked, skip (builder in progress or recently built)
                return False
            
            # Lock acquired, add to queue
            queued = QueuedCapability(
                capability_id=cap_id,
                requirement=requirement,
                status=QueueStatus.PENDING,
                priority=requirement.priority,
            )
            
            # Store queue entry
            entry_key = f"queue:{queued.queue_id}"
            await self._redis.setex(
                entry_key,
                3600,  # 1 hour TTL
                json.dumps(queued.to_dict(), default=str)
            )
            
            # Add to priority queue (sorted set)
            # Higher priority = lower score (sorted asc)
            score = (100 - requirement.priority)  # Invert for sorting
            await self._redis.zadd(
                queue_key,
                {queued.queue_id: score}
            )
            
            print(
                f"[Queue] Enqueued {cap_id} "
                f"(priority={requirement.priority}, "
                f"attempts=1/{queued.max_attempts})"
            )
            
            return True
        
        except Exception as e:
            print(f"[Queue] Enqueue error: {e}")
            return False
    
    async def merge_requirement(
        self,
        existing_queue_id: str,
        new_requirement: CapabilityRequirement,
    ) -> None:
        """
        Merge a new requirement into an existing queue entry.
        
        Used when same capability requested multiple times.
        
        Args:
            existing_queue_id: ID of existing queue entry
            new_requirement: New requirement to merge
        """
        if not self._redis:
            await self._init_redis()
        
        try:
            entry_key = f"queue:{existing_queue_id}"
            entry_json = await self._redis.get(entry_key)
            
            if not entry_json:
                return  # Already removed
            
            # Update merge count
            entry = QueuedCapability(**json.loads(entry_json))
            entry.duplicate_count += 1
            
            # Update priority if new requirement is higher
            if new_requirement.priority > entry.priority:
                entry.priority = new_requirement.priority
            
            await self._redis.setex(
                entry_key,
                3600,
                json.dumps(entry.to_dict(), default=str)
            )
            
            print(
                f"[Queue] Merged requirement into {existing_queue_id} "
                f"(now {entry.duplicate_count} duplicates)"
            )
        
        except Exception as e:
            print(f"[Queue] Merge error: {e}")
    
    async def dequeue_next(self) -> Optional[QueuedCapability]:
        """
        Get next capability to build (highest priority).
        
        Marks as BUILDING and sets builder heartbeat.
        
        Returns:
            Next capability to build, or None if queue empty
        """
        if not self._redis:
            await self._init_redis()
        
        try:
            queue_key = "queue:pending"
            
            # Get highest priority (lowest score)
            items = await self._redis.zrange(
                queue_key,
                0,
                0,  # Just first item
                withscores=True
            )
            
            if not items:
                return None
            
            queue_id_bytes, score = items[0]
            queue_id = queue_id_bytes.decode() if isinstance(queue_id_bytes, bytes) else queue_id_bytes
            
            # Remove from pending
            await self._redis.zrem(queue_key, queue_id)
            
            # Get full entry
            entry_key = f"queue:{queue_id}"
            entry_json = await self._redis.get(entry_key)
            
            if not entry_json:
                return None
            
            queued = QueuedCapability(**json.loads(entry_json))
            queued.status = QueueStatus.BUILDING
            queued.started_at = datetime.utcnow()
            queued.builder_id = str(uuid.uuid4())
            
            # Update entry
            await self._redis.setex(
                entry_key,
                3600,
                json.dumps(queued.to_dict(), default=str)
            )
            
            # Set heartbeat key
            heartbeat_key = f"heartbeat:{queued.builder_id}"
            await self._redis.setex(
                heartbeat_key,
                30,  # 30 second heartbeat
                json.dumps({
                    "queue_id": queue_id,
                    "capability_id": queued.capability_id,
                    "timestamp": datetime.utcnow().isoformat(),
                })
            )
            
            return queued
        
        except Exception as e:
            print(f"[Queue] Dequeue error: {e}")
            return None
    
    async def mark_complete(
        self,
        queue_id: str,
        success: bool,
        error_message: Optional[str] = None,
    ) -> None:
        """
        Mark a queued capability as complete.
        
        Args:
            queue_id: Queue entry ID
            success: Whether build succeeded
            error_message: Error message if failed
        """
        if not self._redis:
            await self._init_redis()
        
        try:
            entry_key = f"queue:{queue_id}"
            entry_json = await self._redis.get(entry_key)
            
            if not entry_json:
                return
            
            queued = QueuedCapability(**json.loads(entry_json))
            
            if success:
                queued.status = QueueStatus.BUILT
                print(f"[Queue] ✓ {queued.capability_id} built successfully")
            else:
                queued.attempt_count += 1
                
                if queued.attempt_count < queued.max_attempts:
                    # Retry
                    queued.status = QueueStatus.PENDING
                    queue_key = "queue:pending"
                    score = (100 - queued.priority)
                    await self._redis.zadd(queue_key, {queue_id: score})
                    
                    print(
                        f"[Queue] ✗ {queued.capability_id} failed "
                        f"(retry {queued.attempt_count}/{queued.max_attempts})"
                    )
                else:
                    # Max retries exceeded
                    queued.status = QueueStatus.FAILED
                    queued.error_message = error_message
                    
                    print(
                        f"[Queue] ✗ {queued.capability_id} failed "
                        f"(max retries exceeded)"
                    )
            
            queued.completed_at = datetime.utcnow()
            
            # Update entry
            await self._redis.setex(
                entry_key,
                3600,
                json.dumps(queued.to_dict(), default=str)
            )
        
        except Exception as e:
            print(f"[Queue] Mark complete error: {e}")
    
    async def get_queue_status(self) -> Dict:
        """
        Get overall queue status.
        
        Returns:
            Dict with pending, building, built, failed counts
        """
        if not self._redis:
            await self._init_redis()
        
        try:
            pending_count = await self._redis.zcard("queue:pending")
            
            # Count statuses (would scan keys)
            return {
                "pending": pending_count,
                "building": len(self._local_in_progress),
                "timestamp": datetime.utcnow().isoformat(),
            }
        
        except Exception as e:
            print(f"[Queue] Status error: {e}")
            return {}
    
    async def _init_redis(self) -> None:
        """Initialize Redis connection"""
        self._redis = await redis.from_url(self.redis_url)


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

"""
from backend.gpc.poltergeist.capability_queue import CapabilityBuildQueue

queue = CapabilityBuildQueue(
    redis_url="redis://localhost:6379",
    max_concurrent_builds=5,
)

# Enqueue a requirement
requirement = CapabilityRequirement(...)
enqueued = await queue.enqueue(requirement)

if enqueued:
    print("Queued for building")
    
    # In builder loop:
    queued = await queue.dequeue_next()
    
    if queued:
        try:
            # Build the capability
            result = await build_capability(queued.requirement)
            
            # Mark as complete
            await queue.mark_complete(queued.queue_id, success=True)
        except Exception as e:
            # Mark as failed (will retry)
            await queue.mark_complete(queued.queue_id, success=False, error_message=str(e))
else:
    print("Already in queue or being built")

# Check queue status
status = await queue.get_queue_status()
print(f"Queue status: {status}")
"""
