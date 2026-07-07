"""Redis-backed priority queue for Veklom task workers."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Optional

import redis.asyncio as aioredis

from backend.core.config import settings

QUEUE_KEY = "veklom:task_queue"

_pool: Optional[aioredis.Redis] = None


def _client() -> aioredis.Redis:
    global _pool
    if _pool is None:
        _pool = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return _pool


@dataclass
class Task:
    id: str
    payload: dict[str, Any]
    priority: int = 5          # 1 (highest) – 10 (lowest)
    enqueued_at: float = field(default_factory=time.time)

    def score(self) -> float:
        """Lower score = dequeued first. Combine priority + enqueue time."""
        return self.priority * 1e12 + self.enqueued_at


async def enqueue(task: Task) -> None:
    """Add a task to the sorted-set priority queue."""
    data = json.dumps({"id": task.id, "payload": task.payload, "priority": task.priority})
    await _client().zadd(QUEUE_KEY, {data: task.score()})


async def dequeue(count: int = 1) -> list[Task]:
    """Pop up to *count* highest-priority tasks (lowest score first)."""
    items = await _client().zpopmin(QUEUE_KEY, count)
    tasks = []
    for data, _ in items:
        obj = json.loads(data)
        tasks.append(Task(id=obj["id"], payload=obj["payload"], priority=obj["priority"]))
    return tasks


async def queue_length() -> int:
    return await _client().zcard(QUEUE_KEY)


async def clear_queue() -> None:
    await _client().delete(QUEUE_KEY)
