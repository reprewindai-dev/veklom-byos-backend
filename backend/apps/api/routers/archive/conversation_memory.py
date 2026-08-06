import logging
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database.database import get_db
from backend.core.memory.conversation import ConversationMemory
from backend.core.security.auth import get_current_user
from backend.core.config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/memory/conversation",
    tags=["Memory", "Agent Army"],
    responses={404: {"description": "Not found"}},
)

@router.get("/{conversation_id}")
async def get_conversation_history(
    conversation_id: str,
    user=Depends(get_current_user)
):
    """
    Get the rolling-window history for a specific conversation.
    This is what the Swarm Council uses to maintain context over 24 hours.
    """
    try:
        history = await ConversationMemory.get_history(user.workspace_id, conversation_id)
        return {
            "conversation_id": conversation_id,
            "message_count": len(history),
            "messages": history
        }
    except Exception as e:
        logger.error(f"Failed to fetch conversation memory: {e}")
        raise HTTPException(status_code=500, detail="Could not retrieve memory")


@router.delete("/{conversation_id}")
async def flush_conversation_history(
    conversation_id: str,
    user=Depends(get_current_user)
):
    """
    Instantly flush/wipe the memory for a specific conversation before the TTL expires.
    """
    from backend.core.database.redis_client import redis_client
    try:
        if not redis_client:
            raise HTTPException(status_code=503, detail="Redis is not connected")
            
        key = ConversationMemory._key(user.workspace_id, conversation_id)
        await redis_client.delete(key)
        
        return {
            "status": "success",
            "message": f"Memory for {conversation_id} flushed successfully."
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to flush memory: {e}")
        raise HTTPException(status_code=500, detail="Could not flush memory")


@router.get("/{conversation_id}/stats")
async def get_memory_stats(
    conversation_id: str,
    user=Depends(get_current_user)
):
    """
    Get TTL statistics and limits for the Conversation Memory.
    """
    from backend.core.database.redis_client import redis_client
    try:
        if not redis_client:
            raise HTTPException(status_code=503, detail="Redis is not connected")
            
        key = ConversationMemory._key(user.workspace_id, conversation_id)
        
        # Check current length
        size = await redis_client.llen(key)
        
        # Check remaining TTL
        ttl = await redis_client.ttl(key)
        
        return {
            "conversation_id": conversation_id,
            "current_messages": size,
            "max_messages_allowed": int(getattr(settings, "MEMORY_MAX_MESSAGES", 20)),
            "remaining_ttl_seconds": ttl,
            "default_ttl_seconds": int(getattr(settings, "MEMORY_TTL_SECONDS", 86400)),
            "status": "active" if size > 0 and ttl > 0 else "empty_or_expired"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get memory stats: {e}")
        raise HTTPException(status_code=500, detail="Could not retrieve memory stats")
