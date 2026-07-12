"""Poltergeist Registry Service for managing distributed builds and intent tracking."""

import json
from typing import Optional, Dict, Any
from backend.core.database.redis_client import redis_client

class PoltergeistRegistry:
    """Manages hot-memory capability resolution states and distributed locks via Redis."""

    def __init__(self):
        self.client = redis_client

    async def _get_lock_key(self, fingerprint: str) -> str:
        return f"poltergeist:build-lock:{fingerprint}"

    async def _get_state_key(self, fingerprint: str) -> str:
        return f"poltergeist:state:{fingerprint}"

    async def acquire_build_lock(self, fingerprint: str, ttl_seconds: int = 300) -> bool:
        """Attempt to acquire a distributed lock for building a specific capability."""
        if not self.client:
            return True  # Fallback if no redis
        lock_key = await self._get_lock_key(fingerprint)
        # NX ensures it only sets if not exists
        acquired = await self.client.set(lock_key, "locked", nx=True, ex=ttl_seconds)
        return bool(acquired)

    async def release_build_lock(self, fingerprint: str):
        """Release the build lock."""
        if not self.client:
            return
        lock_key = await self._get_lock_key(fingerprint)
        await self.client.delete(lock_key)

    async def set_capability_state(self, fingerprint: str, state_data: Dict[str, Any], ttl_seconds: int = 3600):
        """Store the hot state of a capability being built."""
        if not self.client:
            return
        state_key = await self._get_state_key(fingerprint)
        await self.client.set(state_key, json.dumps(state_data), ex=ttl_seconds)

    async def get_capability_state(self, fingerprint: str) -> Optional[Dict[str, Any]]:
        """Retrieve the hot state of a capability."""
        if not self.client:
            return None
        state_key = await self._get_state_key(fingerprint)
        data = await self.client.get(state_key)
        if data:
            return json.loads(data)
        return None

poltergeist_registry = PoltergeistRegistry()
