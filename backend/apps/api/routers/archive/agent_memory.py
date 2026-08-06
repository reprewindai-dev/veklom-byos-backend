"""Agent Memory and Context Layer - Layer 3 of AI Agents Stack 2026"""

import json
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Union
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, func
import logging

from backend.core.database.database import get_db
from backend.core.security.auth import get_current_user
from backend.core.services.embedding_service import get_embedding_service
from backend.db.models.agent_stack import Agent, AgentMemory, ConversationContext, AgentExecution

router = APIRouter(prefix="/api/v1/agents", tags=["Agent Memory"])
logger = logging.getLogger(__name__)


@router.post("/{agent_id}/memory/store")
async def store_agent_memory(
    agent_id: str,
    memory_data: Dict[str, Any],
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Store a memory entry for an agent"""
    try:
        # Verify agent exists and belongs to user's workspace
        agent_result = await db.execute(
            select(Agent).where(
                and_(
                    Agent.id == agent_id,
                    Agent.workspace_id == user.workspace_id
                )
            )
        )
        agent = agent_result.scalar_one_or_none()
        
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Create memory entry
        memory_id = f"mem_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{agent_id[:8]}"
        
        # Generate embedding using real vector service
        embedding_id = None
        relevance_score = None
        
        if memory_data.get("content"):
            try:
                content = memory_data["content"]
                
                # Get embedding service
                embedding_service = await get_embedding_service()
                
                # Store embedding in vector database
                embedding_id = await embedding_service.store_embedding(
                    agent_id=agent_id,
                    memory_id=memory_id,
                    content=content,
                    metadata=memory_data.get("metadata", {})
                )
                
                # Calculate relevance score based on content length and importance
                relevance_score = calculate_relevance_score(content, memory_data.get("metadata", {}))
                
                logger.info(f"Stored real embedding {embedding_id} for memory {memory_id}")
                
            except Exception as e:
                logger.error(f"Failed to generate/store embedding: {e}")
                # Continue without embedding - memory still gets stored
        
        memory = AgentMemory(
            id=memory_id,
            agent_id=agent_id,
            workspace_id=user.workspace_id,
            memory_type=memory_data.get("memory_type", "episodic"),
            content=memory_data.get("content", ""),
            metadata=memory_data.get("metadata", {}),
            expires_at=parse_expiry(memory_data.get("expires_at")),
            embedding_id=embedding_id,
            relevance_score=relevance_score
        )
        
        db.add(memory)
        await db.commit()
        
        return {
            "memory_id": memory_id,
            "stored": True,
            "embedding_generated": embedding_id is not None,
            "relevance_score": relevance_score
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to store agent memory: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to store memory: {str(e)}")


@router.get("/{agent_id}/memory/search")
async def search_agent_memory(
    agent_id: str,
    query: str = None,
    memory_type: str = None,
    limit: int = 10,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Search agent memories with semantic similarity"""
    try:
        # Verify agent exists
        agent_result = await db.execute(
            select(Agent).where(
                and_(
                    Agent.id == agent_id,
                    Agent.workspace_id == user.workspace_id
                )
            )
        )
        agent = agent_result.scalar_one_or_none()
        
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Build base query
        query_builder = select(AgentMemory).where(
            and_(
                AgentMemory.agent_id == agent_id,
                AgentMemory.workspace_id == user.workspace_id
            )
        )
        
        # Filter by memory type if specified
        if memory_type:
            query_builder = query_builder.where(AgentMemory.memory_type == memory_type)
        
        # Filter out expired memories
        query_builder = query_builder.where(
            or_(
                AgentMemory.expires_at.is_(None),
                AgentMemory.expires_at > datetime.now(timezone.utc)
            )
        )
        
        # If semantic search is requested and we have embeddings
        if query:
            try:
                # Get embedding service and perform real vector search
                embedding_service = await get_embedding_service()
                
                # Search for similar embeddings
                similar_embeddings = await embedding_service.search_similar(
                    agent_id=agent_id,
                    query=query,
                    limit=limit,
                    threshold=0.3  # Lower threshold for better recall
                )
                
                if similar_embeddings:
                    # Get full memory objects for the found embeddings
                    memory_ids = [emb["memory_id"] for emb in similar_embeddings]
                    memories_result = await db.execute(
                        query_builder.where(AgentMemory.id.in_(memory_ids))
                    )
                    memories = memories_result.scalars().all()
                    
                    # Combine with similarity scores
                    scored_memories = []
                    for embedding in similar_embeddings:
                        memory = next((m for m in memories if m.id == embedding["memory_id"]), None)
                        if memory:
                            scored_memories.append({
                                "memory": memory,
                                "similarity_score": embedding["similarity"]
                            })
                    
                    return {
                        "memories": [
                            {
                                "id": item["memory"].id,
                                "memory_type": item["memory"].memory_type,
                                "content": item["memory"].content,
                                "metadata": item["memory"].metadata,
                                "created_at": item["memory"].created_at.isoformat(),
                                "access_count": item["memory"].access_count,
                                "similarity_score": item["similarity_score"],
                                "relevance_score": item["memory"].relevance_score
                            }
                            for item in scored_memories
                        ],
                        "total_found": len(scored_memories),
                        "search_type": "semantic"
                    }
                
            except Exception as e:
                logger.warning(f"Semantic search failed, falling back to text search: {e}")
        
        # Fallback to text-based search
        if query:
            query_builder = query_builder.where(
                AgentMemory.content.ilike(f"%{query}%")
            )
        
        # Order by relevance and access count
        query_builder = query_builder.order_by(
            desc(AgentMemory.relevance_score),
            desc(AgentMemory.access_count),
            desc(AgentMemory.created_at)
        ).limit(limit)
        
        memories_result = await db.execute(query_builder)
        memories = memories_result.scalars().all()
        
        return {
            "memories": [
                {
                    "id": memory.id,
                    "memory_type": memory.memory_type,
                    "content": memory.content,
                    "metadata": memory.metadata,
                    "created_at": memory.created_at.isoformat(),
                    "access_count": memory.access_count,
                    "relevance_score": memory.relevance_score
                }
                for memory in memories
            ],
            "total_found": len(memories),
            "search_type": "text"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to search agent memory: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to search memory: {str(e)}")


@router.post("/{agent_id}/context/start")
async def start_conversation_context(
    agent_id: str,
    context_data: Dict[str, Any],
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Start a new conversation context for an agent"""
    try:
        # Verify agent exists
        agent_result = await db.execute(
            select(Agent).where(
                and_(
                    Agent.id == agent_id,
                    Agent.workspace_id == user.workspace_id
                )
            )
        )
        agent = agent_result.scalar_one_or_none()
        
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Create conversation context
        context_id = f"ctx_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{agent_id[:8]}"
        session_id = context_data.get("session_id", f"session_{context_id}")
        
        context = ConversationContext(
            id=context_id,
            agent_id=agent_id,
            workspace_id=user.workspace_id,
            user_id=user.id,
            session_id=session_id,
            turn_number=1,
            context_window={
                "messages": [],
                "current_context": "",
                "entities": {},
                "intent": None
            },
            key_entities=[],
            intent_history=[]
        )
        
        db.add(context)
        await db.commit()
        
        return {
            "context_id": context_id,
            "session_id": session_id,
            "turn_number": 1,
            "created": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start conversation context: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to start context: {str(e)}")


@router.post("/{agent_id}/context/{context_id}/update")
async def update_conversation_context(
    agent_id: str,
    context_id: str,
    update_data: Dict[str, Any],
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update conversation context with new message"""
    try:
        # Get existing context
        context_result = await db.execute(
            select(ConversationContext).where(
                and_(
                    ConversationContext.id == context_id,
                    ConversationContext.agent_id == agent_id,
                    ConversationContext.workspace_id == user.workspace_id
                )
            )
        )
        context = context_result.scalar_one_or_none()
        
        if not context:
            raise HTTPException(status_code=404, detail="Context not found")
        
        # Update context window
        message = update_data.get("message", {})
        context.context_window["messages"].append({
            "role": message.get("role", "user"),
            "content": message.get("content", ""),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "turn": context.turn_number
        })
        
        # Keep only recent messages in context window (last 10 messages)
        if len(context.context_window["messages"]) > 10:
            context.context_window["messages"] = context.context_window["messages"][-10:]
        
        # Update current context summary
        context.context_window["current_context"] = generate_context_summary(
            context.context_window["messages"]
        )
        
        # Extract and update entities
        if update_data.get("entities"):
            context.key_entities.extend(update_data["entities"])
        
        # Update intent history
        if update_data.get("intent"):
            context.intent_history.append({
                "intent": update_data["intent"],
                "turn": context.turn_number,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        
        # Increment turn number
        context.turn_number += 1
        context.updated_at = datetime.now(timezone.utc)
        
        await db.commit()
        
        return {
            "context_id": context_id,
            "turn_number": context.turn_number,
            "message_count": len(context.context_window["messages"]),
            "updated": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update conversation context: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update context: {str(e)}")


@router.get("/{agent_id}/context/{context_id}")
async def get_conversation_context(
    agent_id: str,
    context_id: str,
    include_messages: bool = True,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get conversation context details"""
    try:
        context_result = await db.execute(
            select(ConversationContext).where(
                and_(
                    ConversationContext.id == context_id,
                    ConversationContext.agent_id == agent_id,
                    ConversationContext.workspace_id == user.workspace_id
                )
            )
        )
        context = context_result.scalar_one_or_none()
        
        if not context:
            raise HTTPException(status_code=404, detail="Context not found")
        
        response_data = {
            "context_id": context.id,
            "session_id": context.session_id,
            "turn_number": context.turn_number,
            "current_context": context.context_window.get("current_context", ""),
            "key_entities": context.key_entities,
            "intent_history": context.intent_history,
            "created_at": context.created_at.isoformat(),
            "updated_at": context.updated_at.isoformat()
        }
        
        if include_messages:
            response_data["messages"] = context.context_window.get("messages", [])
        
        return response_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get conversation context: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get context: {str(e)}")


@router.get("/{agent_id}/memory/stats")
async def get_memory_statistics(
    agent_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get memory usage statistics for an agent"""
    try:
        # Verify agent exists
        agent_result = await db.execute(
            select(Agent).where(
                and_(
                    Agent.id == agent_id,
                    Agent.workspace_id == user.workspace_id
                )
            )
        )
        agent = agent_result.scalar_one_or_none()
        
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Get memory statistics
        stats_result = await db.execute(
            select(
                func.count(AgentMemory.id).label("total_memories"),
                func.count(func.distinct(AgentMemory.memory_type)).label("memory_types"),
                func.avg(AgentMemory.access_count).label("avg_access_count"),
                func.max(AgentMemory.created_at).label("latest_memory"),
                func.count(func.distinct(AgentMemory.embedding_id)).label("memories_with_embeddings")
            ).where(
                and_(
                    AgentMemory.agent_id == agent_id,
                    AgentMemory.workspace_id == user.workspace_id
                )
            )
        )
        stats = stats_result.first()
        
        # Get breakdown by memory type
        type_breakdown_result = await db.execute(
            select(
                AgentMemory.memory_type,
                func.count(AgentMemory.id).label("count"),
                func.avg(AgentMemory.relevance_score).label("avg_relevance")
            ).where(
                and_(
                    AgentMemory.agent_id == agent_id,
                    AgentMemory.workspace_id == user.workspace_id
                )
            ).group_by(AgentMemory.memory_type)
        )
        type_breakdown = type_breakdown_result.all()
        
        return {
            "agent_id": agent_id,
            "total_memories": stats.total_memories or 0,
            "memory_types": stats.memory_types or 0,
            "avg_access_count": float(stats.avg_access_count or 0),
            "latest_memory": stats.latest_memory.isoformat() if stats.latest_memory else None,
            "memories_with_embeddings": stats.memories_with_embeddings or 0,
            "type_breakdown": [
                {
                    "memory_type": item.memory_type,
                    "count": item.count,
                    "avg_relevance": float(item.avg_relevance) if item.avg_relevance else 0
                }
                for item in type_breakdown
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get memory statistics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")


@router.delete("/{agent_id}/memory/{memory_id}")
async def delete_memory(
    agent_id: str,
    memory_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a specific memory entry"""
    try:
        # Get and verify memory
        memory_result = await db.execute(
            select(AgentMemory).where(
                and_(
                    AgentMemory.id == memory_id,
                    AgentMemory.agent_id == agent_id,
                    AgentMemory.workspace_id == user.workspace_id
                )
            )
        )
        memory = memory_result.scalar_one_or_none()
        
        if not memory:
            raise HTTPException(status_code=404, detail="Memory not found")
        
        await db.delete(memory)
        await db.commit()
        
        return {"deleted": True, "memory_id": memory_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete memory: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete memory: {str(e)}")


@router.post("/{agent_id}/memory/cleanup")
async def cleanup_expired_memories(
    agent_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Clean up expired memories for an agent"""
    try:
        # Verify agent exists
        agent_result = await db.execute(
            select(Agent).where(
                and_(
                    Agent.id == agent_id,
                    Agent.workspace_id == user.workspace_id
                )
            )
        )
        agent = agent_result.scalar_one_or_none()
        
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        
        # Delete expired memories
        delete_result = await db.execute(
            select(AgentMemory).where(
                and_(
                    AgentMemory.agent_id == agent_id,
                    AgentMemory.workspace_id == user.workspace_id,
                    AgentMemory.expires_at < datetime.now(timezone.utc)
                )
            )
        )
        expired_memories = delete_result.scalars().all()
        
        # Actually delete them
        for memory in expired_memories:
            await db.delete(memory)
        
        await db.commit()
        
        return {
            "cleaned_up": True,
            "deleted_count": len(expired_memories),
            "deleted_memories": [memory.id for memory in expired_memories]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cleanup memories: {str(e)}")
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to cleanup memories: {str(e)}")


# Helper functions
def parse_expiry(expiry_str: Optional[str]) -> Optional[datetime]:
    """Parse expiry time from string"""
    if not expiry_str:
        return None
    
    try:
        if expiry_str.endswith("h"):
            hours = int(expiry_str[:-1])
            return datetime.now(timezone.utc) + timedelta(hours=hours)
        elif expiry_str.endswith("d"):
            days = int(expiry_str[:-1])
            return datetime.now(timezone.utc) + timedelta(days=days)
        elif expiry_str.endswith("w"):
            weeks = int(expiry_str[:-1])
            return datetime.now(timezone.utc) + timedelta(weeks=weeks)
        else:
            # Try parsing as ISO datetime
            return datetime.fromisoformat(expiry_str.replace("Z", "+00:00"))
    except:
        return None


def calculate_relevance_score(content: str, metadata: Dict[str, Any]) -> float:
    """Calculate relevance score for a memory"""
    score = 0.5  # Base score
    
    # Length factor (longer content might be more important)
    length_score = min(len(content) / 1000, 1.0) * 0.3
    score += length_score
    
    # Metadata importance
    if metadata.get("importance") == "high":
        score += 0.3
    elif metadata.get("importance") == "medium":
        score += 0.1
    
    # Recent events are more relevant
    if metadata.get("is_recent"):
        score += 0.2
    
    # User interactions
    if metadata.get("user_interacted"):
        score += 0.2
    
    return min(score, 1.0)


def generate_context_summary(messages: List[Dict[str, Any]]) -> str:
    """Generate a summary of the conversation context"""
    if not messages:
        return ""
    
    # Simple summary - in production, use an LLM for better summaries
    recent_messages = messages[-3:]  # Last 3 messages
    summary_parts = []
    
    for msg in recent_messages:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")[:100]  # First 100 chars
        if len(content) == 100:
            content += "..."
        summary_parts.append(f"{role}: {content}")
    
    return " | ".join(summary_parts)
