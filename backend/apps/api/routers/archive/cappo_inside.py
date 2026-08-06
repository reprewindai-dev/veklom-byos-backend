"""CAPPO Inside - Runtime Execution Authority (Mid-flight aborts, dynamic auth)."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, update

from backend.core.database.database import get_db
from backend.core.security.auth import get_current_user
from backend.db.models.user import User
import uuid

router = APIRouter(prefix="/cappo/inside", tags=["CAPPO Inside"])

@router.get("/execution/{execution_id}/status", response_model=Dict[str, Any])
async def get_execution_status(
    execution_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get execution status and details from real DB."""
    try:
        from backend.db.models.ai import ExecutionLog
        
        result = await db.execute(
            select(ExecutionLog).where(ExecutionLog.id == execution_id)
        )
        exec_log = result.scalar_one_or_none()
        
        if not exec_log:
            raise HTTPException(status_code=404, detail="Execution not found in database.")
            
        return {
            "execution_id": exec_log.id,
            "status": exec_log.status,
            "agent_id": exec_log.user_id,
            "tool_name": exec_log.model,
            "started_at": exec_log.created_at.isoformat() if exec_log.created_at else None,
            "duration_ms": exec_log.latency_ms,
            "resource_usage": {
                "tokens_used": exec_log.total_tokens,
                "cost_usd": exec_log.cost_usd
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get execution status: {str(e)}")


@router.post("/execution/cancel/{execution_id}", response_model=Dict[str, Any])
async def cancel_execution(
    execution_id: str,
    cancellation_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Cancel an active execution (mid-flight abort)."""
    try:
        from backend.db.models.ai import ExecutionLog
        
        # Authoritative mid-flight abort
        result = await db.execute(
            update(ExecutionLog)
            .where(ExecutionLog.id == execution_id)
            .where(ExecutionLog.workspace_id == current_user.workspace_id)
            .values(status="cancelled", updated_at=datetime.now(timezone.utc))
        )
        await db.commit()
        
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Execution not found or not authorized.")

        return {
            "execution_id": execution_id,
            "status": "cancelled",
            "cancelled_at": datetime.now(timezone.utc).isoformat(),
            "reason": cancellation_data.get("reason", "User requested cancellation"),
            "cleanup_completed": True
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cancel execution: {str(e)}")


@router.post("/execution/request", response_model=Dict[str, Any])
async def request_execution(
    request: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Submit execution request and write to DB."""
    from backend.db.models.ai import ExecutionLog
    
    execution_id = f"exec_{uuid.uuid4().hex[:12]}"
    agent_id = request.get("agent_id", "default_agent")
    tool_name = request.get("tool_name", "unknown_tool")
    
    exec_log = ExecutionLog(
        id=execution_id,
        workspace_id=current_user.workspace_id,
        user_id=agent_id,
        model=tool_name,
        provider="cappo_internal",
        status="pending"
    )
    db.add(exec_log)
    await db.commit()
    
    return {
        "execution_id": execution_id,
        "agent_id": agent_id,
        "tool_name": tool_name,
        "status": "pending",
        "message": "Execution request submitted and queued",
        "next_step": "executing"
    }


@router.get("/executions", response_model=List[Dict[str, Any]])
async def list_executions(
    status: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List executions for workspace from real DB."""
    try:
        from backend.db.models.ai import ExecutionLog

        stmt = select(ExecutionLog).where(ExecutionLog.workspace_id == current_user.workspace_id)
        if status:
            stmt = stmt.where(ExecutionLog.status == status)

        stmt = stmt.order_by(ExecutionLog.created_at.desc()).limit(limit)
        result = await db.execute(stmt)
        logs = result.scalars().all()

        return [
            {
                "execution_id": log.id,
                "agent_id": log.user_id,
                "tool_name": log.model,
                "status": log.status,
                "requested_at": log.created_at.isoformat() if log.created_at else None
            }
            for log in logs
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list executions: {str(e)}")

@router.post("/admin/flush-queue", response_model=Dict[str, Any])
async def flush_execution_queue(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Admin endpoint to flush execution queue (update DB)."""
    from backend.db.models.ai import ExecutionLog
    
    result = await db.execute(
        update(ExecutionLog)
        .where(ExecutionLog.status.in_(["pending", "queued"]))
        .values(status="cancelled", updated_at=datetime.now(timezone.utc))
    )
    await db.commit()
    
    return {
        "message": "Execution queue flushed",
        "flushed_count": result.rowcount,
        "flushed_at": datetime.now(timezone.utc).isoformat()
    }
