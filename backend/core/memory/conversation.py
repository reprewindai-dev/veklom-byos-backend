"""Redis-backed tenant-isolated conversation memory."""
import json
import logging
from typing import List, Dict
from backend.core.config.settings import settings
from backend.core.database.redis_client import redis_client

logger = logging.getLogger(__name__)

class ConversationMemory:
    @staticmethod
    def _key(workspace_id: str, conversation_id: str) -> str:
        return f"conv:{workspace_id}:{conversation_id}"

    @classmethod
    async def get_history(cls, workspace_id: str, conversation_id: str) -> List[Dict[str, str]]:
        """Retrieve conversation history namespaced by workspace_id."""
        if not redis_client or not conversation_id or not workspace_id:
            return []
            
        key = cls._key(workspace_id, conversation_id)
        try:
            items = await redis_client.lrange(key, 0, -1)
            history = []
            for item in items:
                history.append(json.loads(item))
            return history
        except Exception as e:
            logger.error(f"Failed to retrieve conversation memory for key {key}: {e}")
            return []

    @classmethod
    async def add_messages(cls, workspace_id: str, conversation_id: str, messages: List[Dict[str, str]]):
        """Append messages, trim to MEMORY_MAX_MESSAGES, and reset TTL."""
        if not redis_client or not conversation_id or not workspace_id or not messages:
            return
            
        key = cls._key(workspace_id, conversation_id)
        ttl = int(getattr(settings, "MEMORY_TTL_SECONDS", 86400))
        max_msgs = int(getattr(settings, "MEMORY_MAX_MESSAGES", 20))

        try:
            for msg in messages:
                serialized = json.dumps({"role": msg["role"], "content": msg["content"]})
                await redis_client.rpush(key, serialized)
                
            # Trim from left if size exceeds max_msgs
            size = await redis_client.llen(key)
            if size > max_msgs:
                await redis_client.ltrim(key, size - max_msgs, -1)
                
            # Reset TTL
            await redis_client.expire(key, ttl)
        except Exception as e:
            logger.error(f"Failed to save conversation memory for key {key}: {e}")
