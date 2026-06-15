"""CAPPO Internal Integration - Execution Authority (no frontend)."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from backend.core.database.database import get_db
from backend.core.security.auth import get_current_user
from backend.db.models.user import User
import uuid
import hashlib
import json
import asyncio
from enum import Enum

router = APIRouter(prefix="/cappo", tags=["CAPPO Internal"])


@router.get("/execution/status/{execution_id}", response_model=Dict[str, Any])
async def get_execution_status(
    execution_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get execution status and details."""
    
    try:
        # Mock execution status for demo
        return {
            "execution_id": execution_id,
            "status": ExecutionStatus.COMPLETED,
            "priority": ExecutionPriority.NORMAL,
            "agent_id": "agent_001",
            "tool_name": "web_search",
            "tool_parameters": {"query": "test", "limit": 10},
            "authority_run_id": "run_abc123",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "duration_ms": 1250,
            "result": {
                "success": True,
                "data": {"results": ["result1", "result2"]},
                "error": None
            },
            "resource_usage": {
                "cpu_ms": 850,
                "memory_mb": 45,
                "network_kb": 120
            },
            "policy_compliance": {
                "violations": [],
                "warnings": [],
                "approved": True
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get execution status: {str(e)}"
        )


@router.post("/execution/cancel/{execution_id}", response_model=Dict[str, Any])
async def cancel_execution(
    execution_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Cancel an active execution."""
    
    try:
        return {
            "execution_id": execution_id,
            "status": ExecutionStatus.CANCELLED,
            "cancelled_at": datetime.now(timezone.utc).isoformat(),
            "reason": "User requested cancellation",
            "cleanup_completed": True
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cancel execution: {str(e)}"
        )


@router.get("/executions/active", response_model=List[Dict[str, Any]])
async def list_active_executions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all active executions."""
    
    try:
        return [
            {
                "execution_id": "exec_001",
                "agent_id": "agent_001",
                "tool_name": "data_analysis",
                "status": ExecutionStatus.RUNNING,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "priority": ExecutionPriority.HIGH,
                "progress": 65
            },
            {
                "execution_id": "exec_002",
                "agent_id": "agent_002",
                "tool_name": "web_search",
                "status": ExecutionStatus.RUNNING,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "priority": ExecutionPriority.NORMAL,
                "progress": 30
            }
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list active executions: {str(e)}"
        )


@router.get("/executions/history", response_model=List[Dict[str, Any]])
async def get_execution_history(
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get execution history."""
    
    try:
        return [
            {
                "execution_id": "exec_003",
                "agent_id": "agent_001",
                "tool_name": "automation",
                "status": ExecutionStatus.COMPLETED,
                "started_at": "2026-01-15T09:30:00Z",
                "completed_at": "2026-01-15T09:32:15Z",
                "duration_ms": 135000,
                "success": True,
                "priority": ExecutionPriority.NORMAL
            },
            {
                "execution_id": "exec_004",
                "agent_id": "agent_002",
                "tool_name": "data_processing",
                "status": ExecutionStatus.FAILED,
                "started_at": "2026-01-15T08:45:00Z",
                "completed_at": "2026-01-15T08:46:30Z",
                "duration_ms": 90000,
                "success": False,
                "error": "Timeout exceeded",
                "priority": ExecutionPriority.LOW
            }
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get execution history: {str(e)}"
        )


@router.post("/policy/validate", response_model=Dict[str, Any])
async def validate_execution_policy(
    policy_request: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Validate execution against security policies."""
    
    try:
        required_fields = ["agent_id", "tool_name", "tool_parameters"]
        for field in required_fields:
            if field not in policy_request:
                raise HTTPException(
                    status_code=400,
                    detail=f"Missing required field: {field}"
                )
        
        # Mock policy validation
        violations = []
        warnings = []
        
        # Check for dangerous operations
        if policy_request["tool_name"] in ["system_delete", "external_payment"]:
            violations.append({
                "rule": "dangerous_operation",
                "severity": "high",
                "message": f"Tool {policy_request['tool_name']} requires explicit approval"
            })
        
        # Check resource limits
        if policy_request["tool_parameters"].get("memory_limit", 0) > 1024:
            warnings.append({
                "rule": "resource_limit",
                "severity": "medium", 
                "message": "High memory usage requested"
            })
        
        return {
            "validation_id": f"val_{uuid.uuid4().hex[:8]}",
            "approved": len(violations) == 0,
            "violations": violations,
            "warnings": warnings,
            "policy_version": "1.0.0",
            "validated_at": datetime.now(timezone.utc).isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to validate policy: {str(e)}"
        )


@router.get("/resources/usage", response_model=Dict[str, Any])
async def get_resource_usage(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current resource usage statistics."""
    
    try:
        return {
            "current_usage": {
                "active_executions": 3,
                "cpu_usage_percent": 45.2,
                "memory_usage_mb": 512,
                "network_io_kb_per_sec": 125.5,
                "disk_io_mb_per_sec": 12.3
            },
            "limits": {
                "max_concurrent_executions": 10,
                "max_cpu_percent": 80,
                "max_memory_mb": 2048,
                "max_network_kb_per_sec": 1000
            },
            "utilization": {
                "cpu_utilization": 56.5,
                "memory_utilization": 25.0,
                "execution_capacity": 30.0
            },
            "today": {
                "total_executions": 47,
                "successful_executions": 45,
                "failed_executions": 2,
                "total_execution_time_ms": 125000
            }
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get resource usage: {str(e)}"
        )


@router.post("/queue/priority", response_model=Dict[str, Any])
async def set_execution_priority(
    priority_request: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Set execution priority for queued jobs."""
    
    try:
        required_fields = ["execution_id", "priority"]
        for field in required_fields:
            if field not in priority_request:
                raise HTTPException(
                    status_code=400,
                    detail=f"Missing required field: {field}"
                )
        
        # Validate priority
        if priority_request["priority"] not in [p.value for p in ExecutionPriority]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid priority. Must be one of: {[p.value for p in ExecutionPriority]}"
            )
        
        return {
            "execution_id": priority_request["execution_id"],
            "old_priority": "normal",
            "new_priority": priority_request["priority"],
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "queue_position": 1 if priority_request["priority"] == "critical" else 3
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to set execution priority: {str(e)}"
        )


class ExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExecutionPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


@router.post("/execution/request", response_model=Dict[str, Any])
async def request_execution(
    execution_request: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Request execution through CAPPO authority."""
    
    required_fields = ["agent_id", "tool_name", "tool_parameters", "authority_run_id"]
    for field in required_fields:
        if field not in execution_request:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required field: {field}"
            )
    
    execution_id = f"exec_{uuid.uuid4().hex[:8]}"
    
    # Create execution request
    execution = {
        "execution_id": execution_id,
        "agent_id": execution_request["agent_id"],
        "tool_name": execution_request["tool_name"],
        "tool_parameters": execution_request["tool_parameters"],
        "authority_run_id": execution_request["authority_run_id"],
        "workspace_id": current_user.workspace_id,
        "status": ExecutionStatus.PENDING,
        "priority": execution_request.get("priority", ExecutionPriority.NORMAL),
        "requested_at": datetime.now(timezone.utc).isoformat(),
        "requested_by": current_user.id,
        "budget_limit": execution_request.get("budget_limit"),
        "timeout_seconds": execution_request.get("timeout_seconds", 300),
        "requires_approval": execution_request.get("requires_approval", False),
        "approval_status": "pending" if execution_request.get("requires_approval", False) else "auto_approved"
    }
    
    # Store execution request (in real implementation, would save to database)
    
    # Check if execution requires approval
    if execution["requires_approval"]:
        return {
            **execution,
            "message": "Execution request submitted for approval",
            "next_step": "await_approval"
        }
    else:
        # Auto-approve and queue for execution
        await queue_execution(execution)
        return {
            **execution,
            "message": "Execution request auto-approved and queued",
            "next_step": "executing"
        }


@router.post("/execution/{execution_id}/approve", response_model=Dict[str, Any])
async def approve_execution(
    execution_id: str,
    approval_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Approve execution request."""
    
    # In real implementation, would verify execution exists and user has approval authority
    
    approval = {
        "execution_id": execution_id,
        "approved_by": current_user.id,
        "approved_at": datetime.now(timezone.utc).isoformat(),
        "approval_reason": approval_data.get("reason", ""),
        "conditions": approval_data.get("conditions", []),
        "budget_override": approval_data.get("budget_override"),
        "timeout_override": approval_data.get("timeout_override")
    }
    
    # Queue execution after approval
    execution = {
        "execution_id": execution_id,
        "status": ExecutionStatus.PENDING,
        "approval_status": "approved"
    }
    
    await queue_execution(execution)
    
    return {
        **approval,
        "message": "Execution approved and queued"
    }


@router.post("/execution/{execution_id}/deny", response_model=Dict[str, Any])
async def deny_execution(
    execution_id: str,
    denial_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Deny execution request."""
    
    denial = {
        "execution_id": execution_id,
        "denied_by": current_user.id,
        "denied_at": datetime.now(timezone.utc).isoformat(),
        "denial_reason": denial_data.get("reason", ""),
        "policy_violations": denial_data.get("policy_violations", []),
        "security_concerns": denial_data.get("security_concerns", [])
    }
    
    # Update execution status
    execution = {
        "execution_id": execution_id,
        "status": ExecutionStatus.CANCELLED,
        "approval_status": "denied"
    }
    
    return {
        **denial,
        **execution,
        "message": "Execution denied"
    }


@router.get("/execution/{execution_id}/status", response_model=Dict[str, Any])
async def get_execution_status(
    execution_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get execution status."""
    
    # Mock response - in real implementation, query database
    return {
        "execution_id": execution_id,
        "status": ExecutionStatus.RUNNING,
        "progress": 65,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "estimated_completion": datetime.now(timezone.utc).isoformat(),
        "resource_usage": {
            "cpu_percent": 45,
            "memory_mb": 512,
            "tokens_used": 1250,
            "cost_usd": 0.0234
        },
        "logs": [
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": "INFO",
                "message": "Execution started"
            },
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": "INFO", 
                "message": "Processing tool parameters"
            },
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "level": "INFO",
                "message": "Executing tool: web_search"
            }
        ],
        "errors": [],
        "warnings": []
    }


@router.post("/execution/{execution_id}/cancel", response_model=Dict[str, Any])
async def cancel_execution(
    execution_id: str,
    cancellation_data: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Cancel running execution."""
    
    cancellation = {
        "execution_id": execution_id,
        "cancelled_by": current_user.id,
        "cancelled_at": datetime.now(timezone.utc).isoformat(),
        "reason": cancellation_data.get("reason", "User requested cancellation"),
        "force": cancellation_data.get("force", False)
    }
    
    return {
        **cancellation,
        "status": ExecutionStatus.CANCELLED,
        "message": "Execution cancelled"
    }


@router.get("/executions", response_model=List[Dict[str, Any]])
async def list_executions(
    status: Optional[str] = Query(None),
    agent_id: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List executions for workspace."""
    
    # Mock response - in real implementation, query database with filters
    return [
        {
            "execution_id": "exec_12345678",
            "agent_id": "agent_87654321",
            "tool_name": "web_search",
            "status": ExecutionStatus.COMPLETED,
            "priority": ExecutionPriority.NORMAL,
            "requested_at": datetime.now(timezone.utc).isoformat(),
            "started_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "duration_seconds": 12.5,
            "cost_usd": 0.0234,
            "tokens_used": 1250,
            "approval_status": "auto_approved"
        },
        {
            "execution_id": "exec_87654321",
            "agent_id": "agent_12345678",
            "tool_name": "file_access",
            "status": ExecutionStatus.RUNNING,
            "priority": ExecutionPriority.HIGH,
            "requested_at": datetime.now(timezone.utc).isoformat(),
            "started_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": None,
            "duration_seconds": None,
            "cost_usd": 0.0156,
            "tokens_used": 845,
            "approval_status": "approved"
        }
    ]


@router.get("/executions/{execution_id}/evidence", response_model=Dict[str, Any])
async def get_execution_evidence(
    execution_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get execution evidence for audit trail."""
    
    # Mock response - in real implementation, query evidence database
    return {
        "execution_id": execution_id,
        "evidence_pack_id": f"evidence_{uuid.uuid4().hex[:8]}",
        "workspace_id": current_user.workspace_id,
        "agent_id": "agent_12345678",
        "authority_run_id": "run_87654321",
        "created_at": datetime.now(timezone.utc).isoformat(),
        
        "execution_chain": [
            {
                "step": "request",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "actor": current_user.id,
                "data": "Execution request submitted",
                "hash": "sha256:step1_hash"
            },
            {
                "step": "approval",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "actor": "system",
                "data": "Auto-approved based on policy",
                "hash": "sha256:step2_hash"
            },
            {
                "step": "execution",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "actor": "cappo_executor",
                "data": "Tool executed successfully",
                "hash": "sha256:step3_hash"
            }
        ],
        
        "resource_usage": {
            "cpu_time_seconds": 2.3,
            "memory_peak_mb": 512,
            "network_bytes": 1024,
            "tokens_processed": 1250,
            "cost_usd": 0.0234
        },
        
        "policy_compliance": {
            "seked_applied": True,
            "seked_ratio": 3.2,
            "seked_directive": "Execute primary objectives",
            "policy_violations": [],
            "security_checks": "passed"
        },
        
        "audit_hash": hashlib.sha256(
            f"{execution_id}{datetime.now(timezone.utc).isoformat()}".encode()
        ).hexdigest()
    }


@router.get("/queue", response_model=Dict[str, Any])
async def get_execution_queue(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current execution queue status."""
    
    # Mock response - in real implementation, query actual queue
    return {
        "queue_status": "active",
        "total_pending": 3,
        "total_running": 2,
        "max_concurrent": 5,
        "queue_capacity": 10,
        
        "pending_executions": [
            {
                "execution_id": "exec_pending_1",
                "agent_id": "agent_123",
                "tool_name": "api_call",
                "priority": ExecutionPriority.HIGH,
                "queued_at": datetime.now(timezone.utc).isoformat(),
                "estimated_wait_seconds": 30
            },
            {
                "execution_id": "exec_pending_2", 
                "agent_id": "agent_456",
                "tool_name": "database_query",
                "priority": ExecutionPriority.NORMAL,
                "queued_at": datetime.now(timezone.utc).isoformat(),
                "estimated_wait_seconds": 60
            }
        ],
        
        "running_executions": [
            {
                "execution_id": "exec_running_1",
                "agent_id": "agent_789",
                "tool_name": "file_access",
                "priority": ExecutionPriority.NORMAL,
                "started_at": datetime.now(timezone.utc).isoformat(),
                "progress_percent": 45,
                "estimated_remaining_seconds": 120
            }
        ],
        
        "resource_limits": {
            "max_cpu_percent": 80,
            "max_memory_mb": 4096,
            "max_concurrent_executions": 5,
            "budget_hourly_usd": 10.0
        },
        
        "current_usage": {
            "cpu_percent": 45,
            "memory_mb": 2048,
            "active_executions": 2,
            "cost_this_hour_usd": 2.34
        }
    }


@router.post("/admin/flush-queue", response_model=Dict[str, Any])
async def flush_execution_queue(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Admin endpoint to flush execution queue."""
    
    # In real implementation, would verify admin permissions
    return {
        "message": "Execution queue flushed",
        "flushed_count": 3,
        "flushed_executions": ["exec_pending_1", "exec_pending_2", "exec_pending_3"],
        "flushed_at": datetime.now(timezone.utc).isoformat()
    }


@router.get("/health", response_model=Dict[str, Any])
async def get_cappo_health(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get CAPPO system health status."""
    
    return {
        "status": "healthy",
        "version": "1.0.0",
        "uptime_seconds": 86400,
        "last_execution": datetime.now(timezone.utc).isoformat(),
        
        "components": {
            "executor": "healthy",
            "queue": "healthy", 
            "approver": "healthy",
            "evidence_collector": "healthy"
        },
        
        "metrics": {
            "executions_today": 156,
            "executions_completed": 148,
            "executions_failed": 3,
            "average_execution_time_seconds": 15.2,
            "total_cost_today_usd": 2.45
        },
        
        "alerts": [],
        "last_health_check": datetime.now(timezone.utc).isoformat()
    }


# Helper function
async def queue_execution(execution: Dict[str, Any]):
    """Queue execution for processing."""
    # In real implementation, would add to actual execution queue
    # For now, this is a placeholder
    pass
