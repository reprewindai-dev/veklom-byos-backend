import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

import aiofiles

logger = logging.getLogger(__name__)

MANIFEST_STORE_PATH = "/tmp/mcp_manifests.json"

# L1 Cache: In-memory dictionary
_LOCAL_MANIFESTS_CACHE = {}
_LOCAL_CACHE_TIME = 0.0
CACHE_TTL = 300.0  # 5 minutes TTL

class ToolManifestStore:
    """Stores and retrieves compiled MCP tool manifests with hot-path L1 caching."""

    @classmethod
    async def _ensure_store_async(cls):
        os.makedirs(os.path.dirname(MANIFEST_STORE_PATH), exist_ok=True)
        if not os.path.exists(MANIFEST_STORE_PATH):
            async with aiofiles.open(MANIFEST_STORE_PATH, "w") as f:
                await f.write(json.dumps({}))

    @classmethod
    def _ensure_store(cls):
        os.makedirs(os.path.dirname(MANIFEST_STORE_PATH), exist_ok=True)
        if not os.path.exists(MANIFEST_STORE_PATH):
            with open(MANIFEST_STORE_PATH, "w") as f:
                json.dump({}, f)

    @classmethod
    async def get_all_manifests(cls) -> Dict[str, Dict[str, Any]]:
        """Retrieve all stored manifests, utilizing L1 cache."""
        global _LOCAL_MANIFESTS_CACHE, _LOCAL_CACHE_TIME
        now = time.time()
        if _LOCAL_MANIFESTS_CACHE and (now - _LOCAL_CACHE_TIME) < CACHE_TTL:
            return _LOCAL_MANIFESTS_CACHE

        await cls._ensure_store_async()
        try:
            async with aiofiles.open(MANIFEST_STORE_PATH, "r") as f:
                content = await f.read()
                data = json.loads(content)
                _LOCAL_MANIFESTS_CACHE.clear()
                _LOCAL_MANIFESTS_CACHE.update(data)
                _LOCAL_CACHE_TIME = now
                return data
        except Exception as e:
            logger.error(f"Error reading manifest store: {e}")
            return {}

    @classmethod
    async def get_tool(cls, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get a specific tool manifest by name."""
        manifests = await cls.get_all_manifests()
        return manifests.get(tool_name)

    @classmethod
    async def save_manifests(cls, new_manifests: List[Dict[str, Any]]):
        """Save a list of new manifests to the store."""
        manifests = await cls.get_all_manifests()

        for m in new_manifests:
            manifests[m["tool_name"]] = m

        await cls._ensure_store_async()
        try:
            async with aiofiles.open(MANIFEST_STORE_PATH, "w") as f:
                await f.write(json.dumps(manifests, indent=2))

            # Invalidate/Update Cache
            global _LOCAL_CACHE_TIME
            _LOCAL_MANIFESTS_CACHE.clear()
            _LOCAL_MANIFESTS_CACHE.update(manifests)
            _LOCAL_CACHE_TIME = time.time()
        except Exception as e:
            logger.error(f"Error writing to manifest store: {e}")
            raise
