import asyncio
import json
import logging
import os
import tempfile
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

MANIFEST_STORE_PATH = "/tmp/mcp_manifests.json"

# L1 Cache: In-memory dictionary
_LOCAL_MANIFESTS_CACHE: Dict[str, Dict[str, Any]] = {}
_LOCAL_CACHE_TIME = 0.0
CACHE_TTL = 300.0  # 5 minutes TTL


class ToolManifestStore:
    """Stores and retrieves compiled MCP tool manifests with hot-path L1 caching."""

    @classmethod
    def _ensure_store(cls) -> None:
        os.makedirs(os.path.dirname(MANIFEST_STORE_PATH), exist_ok=True)
        if not os.path.exists(MANIFEST_STORE_PATH):
            cls._write_store({})

    @staticmethod
    def _read_store() -> Dict[str, Dict[str, Any]]:
        with open(MANIFEST_STORE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError("manifest store root must be a JSON object")
        return data

    @staticmethod
    def _write_store(manifests: Dict[str, Dict[str, Any]]) -> None:
        """Write atomically so a crash cannot leave a truncated manifest store."""
        directory = os.path.dirname(MANIFEST_STORE_PATH)
        os.makedirs(directory, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(prefix="mcp_manifests_", suffix=".json", dir=directory)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(manifests, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_path, MANIFEST_STORE_PATH)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    @classmethod
    async def get_all_manifests(cls) -> Dict[str, Dict[str, Any]]:
        """Retrieve all stored manifests without blocking the event loop."""
        global _LOCAL_CACHE_TIME
        now = time.time()
        if _LOCAL_MANIFESTS_CACHE and (now - _LOCAL_CACHE_TIME) < CACHE_TTL:
            return dict(_LOCAL_MANIFESTS_CACHE)

        try:
            await asyncio.to_thread(cls._ensure_store)
            data = await asyncio.to_thread(cls._read_store)
            _LOCAL_MANIFESTS_CACHE.clear()
            _LOCAL_MANIFESTS_CACHE.update(data)
            _LOCAL_CACHE_TIME = now
            return dict(data)
        except Exception as e:
            logger.error("Error reading manifest store: %s", e)
            return {}

    @classmethod
    async def get_tool(cls, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get a specific tool manifest by name."""
        manifests = await cls.get_all_manifests()
        return manifests.get(tool_name)

    @classmethod
    async def save_manifests(cls, new_manifests: List[Dict[str, Any]]) -> None:
        """Save manifests without blocking the event loop and update the L1 cache."""
        manifests = await cls.get_all_manifests()

        for manifest in new_manifests:
            tool_name = manifest.get("tool_name")
            if not tool_name:
                raise ValueError("manifest is missing required tool_name")
            manifests[tool_name] = manifest

        try:
            await asyncio.to_thread(cls._write_store, manifests)

            global _LOCAL_CACHE_TIME
            _LOCAL_MANIFESTS_CACHE.clear()
            _LOCAL_MANIFESTS_CACHE.update(manifests)
            _LOCAL_CACHE_TIME = time.time()
        except Exception as e:
            logger.error("Error writing to manifest store: %s", e)
            raise
