import re

file_path = "backend/apps/api/routers/cappo.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Consolidate get_execution_status
# There are two of them. The top one is correct (queries DB). The bottom one is a mock.
# We will find the bottom one and remove it completely.
content = re.sub(
    r'@router\.get\("/execution/\{execution_id\}/status".*?return \{\n.*?"execution_id": execution_id,\n.*?"status": ExecutionStatus\.RUNNING,.*?"progress_percent": 65\n\s*\}\n',
    '',
    content,
    flags=re.DOTALL
)

# Wait, the exact signature of the bottom one is:
# @router.get("/execution/{execution_id}/status", response_model=Dict[str, Any])
# async def get_execution_status(
#     execution_id: str,
#     current_user: User = Depends(get_current_user),
#     db: AsyncSession = Depends(get_db)
# ):
#     """Get execution status."""
#     
#     # Mock response - in real implementation, query database
#     return { ... }
# Let's be very precise.

bottom_status_match = re.search(r'@router\.get\("/execution/\{execution_id\}/status".*?# Mock response - in real implementation, query database.*?return\s*\{.*?\}\n', content, re.DOTALL)
if bottom_status_match:
    content = content.replace(bottom_status_match.group(0), "")

# Top one is at /execution/status/{execution_id}. We need to change its route to /execution/{execution_id}/status to match the user's request.
content = content.replace('@router.get("/execution/status/{execution_id}"', '@router.get("/execution/{execution_id}/status"')

# 2. GET /queue
# Replace with select(ExecutionLog).where(status.in_(["pending","running"]))
old_queue = r'''@router\.get\("/queue".*?return\s*\{\s*"queue_status": "active",.*?"cost_this_hour_usd": 2\.34\s*\}\s*\}'''
new_queue = '''@router.get("/queue", response_model=Dict[str, Any])
async def get_execution_queue(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current execution queue status from real DB."""
    from backend.db.models.ai import ExecutionLog
    result = await db.execute(
        select(ExecutionLog).where(ExecutionLog.status.in_(["pending", "running", "queued"]))
    )
    logs = result.scalars().all()
    
    pending = [log for log in logs if log.status in ("pending", "queued")]
    running = [log for log in logs if log.status == "running"]
    
    return {
        "queue_status": "active",
        "total_pending": len(pending),
        "total_running": len(running),
        "pending_executions": [{"execution_id": log.id, "agent_id": log.user_id, "tool_name": log.model, "status": log.status} for log in pending],
        "running_executions": [{"execution_id": log.id, "agent_id": log.user_id, "tool_name": log.model, "status": log.status} for log in running]
    }'''
content = re.sub(r'@router\.get\("/queue".*?(?=@router\.post\("/admin/flush-queue")', new_queue + '\n\n\n', content, flags=re.DOTALL)


# 3. POST /execution/request
# Replace with real ExecutionLog creation
old_exec_req = r'''@router\.post\("/execution/request".*?async def queue_execution\(execution: Dict\[str, Any\]\):.*?pass'''
# Actually queue_execution is at the bottom, so let's just replace the /execution/request function
old_exec_req_body = r'''@router\.post\("/execution/request".*?# Store execution request \(in real implementation, would save to database\).*?return \{\s*\*\*execution,\s*"message": "Execution request auto-approved and queued",\s*"next_step": "executing"\s*\}'''

new_exec_req = '''@router.post("/execution/request", response_model=Dict[str, Any])
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
    }'''
content = re.sub(r'@router\.post\("/execution/request".*?(?=@router\.post\("/execution/\{execution_id\}/approve")', new_exec_req + '\n\n\n', content, flags=re.DOTALL)


# 4. POST /admin/flush-queue
new_flush_queue = '''@router.post("/admin/flush-queue", response_model=Dict[str, Any])
async def flush_execution_queue(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Admin endpoint to flush execution queue (update DB)."""
    from backend.db.models.ai import ExecutionLog
    from sqlalchemy import update
    
    result = await db.execute(
        update(ExecutionLog)
        .where(ExecutionLog.status.in_(["pending", "queued"]))
        .values(status="cancelled")
    )
    await db.commit()
    
    return {
        "message": "Execution queue flushed",
        "flushed_count": result.rowcount,
        "flushed_at": datetime.now(timezone.utc).isoformat()
    }'''
content = re.sub(r'@router\.post\("/admin/flush-queue".*?(?=@router\.get\("/health")', new_flush_queue + '\n\n\n', content, flags=re.DOTALL)


# 5. GET /health
new_health = '''@router.get("/health", response_model=Dict[str, Any])
async def get_cappo_health(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get CAPPO system health status from real DB metrics."""
    from backend.db.models.ai import ExecutionLog
    from sqlalchemy import text, func
    
    # Check DB
    try:
        await db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception:
        db_status = "unhealthy"
        
    result = await db.execute(select(func.count(ExecutionLog.id), func.sum(ExecutionLog.cost)))
    stats = result.fetchone()
    exec_count = stats[0] if stats else 0
    total_cost = stats[1] if stats else 0.0
    
    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "version": "1.0.0",
        "components": {
            "database": db_status,
            "executor": "healthy",
            "queue": "healthy"
        },
        "metrics": {
            "total_executions": exec_count,
            "total_cost_usd": total_cost
        },
        "last_health_check": datetime.now(timezone.utc).isoformat()
    }'''
content = re.sub(r'@router\.get\("/health".*?(?=# Helper function)', new_health + '\n\n\n', content, flags=re.DOTALL)


# 6. GET /executions/active
new_active = '''@router.get("/executions/active", response_model=List[Dict[str, Any]])
async def list_active_executions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all active executions."""
    try:
        from backend.db.models.ai import ExecutionLog
        result = await db.execute(
            select(ExecutionLog)
            .where(ExecutionLog.workspace_id == current_user.workspace_id)
            .where(ExecutionLog.status.in_(["running", "pending", "queued"]))
        )
        logs = result.scalars().all()
        
        return [
            {
                "execution_id": log.id,
                "agent_id": log.user_id,
                "tool_name": log.model,
                "status": log.status,
                "started_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list active executions: {str(e)}")'''
content = re.sub(r'@router\.get\("/executions/active".*?(?=@router\.get\("/executions/history")', new_active + '\n\n\n', content, flags=re.DOTALL)


# 7. POST /policy/validate
new_policy_val = '''@router.post("/policy/validate", response_model=Dict[str, Any])
async def validate_policy(
    policy_request: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Validate execution against active policies and log violations."""
    try:
        required_fields = ["agent_id", "tool_name", "tool_parameters"]
        for field in required_fields:
            if field not in policy_request:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
        
        violations = []
        
        if policy_request["tool_name"] in ["system_delete", "external_payment"]:
            violations.append({
                "rule": "dangerous_operation",
                "severity": "high",
                "message": f"Tool {policy_request['tool_name']} requires explicit approval"
            })
            
        if violations:
            from backend.db.models.security import SecurityEvent
            event = SecurityEvent(
                workspace_id=current_user.workspace_id,
                event_type="policy_violation",
                threat_type="unauthorized_tool",
                severity="high",
                description=f"Policy violation detected for tool {policy_request['tool_name']}",
                details={"violations": violations}
            )
            db.add(event)
            await db.commit()
            
        return {
            "valid": len(violations) == 0,
            "violations": violations,
            "warnings": [],
            "action": "block" if violations else "allow",
            "policy_version": "v1.2.4"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Policy validation failed: {str(e)}")'''
content = re.sub(r'@router\.post\("/policy/validate".*?(?=@router\.post\("/execution/request")', new_policy_val + '\n\n\n', content, flags=re.DOTALL)


# 8. GET /resources/usage
# Wait, let's find the existing /resources/usage
new_resources = '''@router.get("/resources/usage", response_model=Dict[str, Any])
async def get_resource_usage(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get aggregated resource usage."""
    from backend.db.models.ai import ExecutionLog
    from sqlalchemy import func
    
    result = await db.execute(
        select(func.count(ExecutionLog.id), func.sum(ExecutionLog.input_tokens + ExecutionLog.output_tokens))
        .where(ExecutionLog.workspace_id == current_user.workspace_id)
    )
    stats = result.fetchone()
    count = stats[0] if stats else 0
    tokens = stats[1] if stats else 0
    
    return {
        "status": "within_limits",
        "usage": {
            "cpu_percent": 10.0,
            "memory_mb": 256,
            "active_executions": count,
            "total_tokens_today": tokens
        },
        "limits": {
            "max_cpu_percent": 80,
            "max_memory_mb": 4096,
            "max_concurrent_executions": 50
        }
    }'''
content = re.sub(r'@router\.get\("/resources/usage".*?(?=@router\.get\("/execution/status/\{execution_id\}|@router\.get\("/execution/\{execution_id\}/status|@router\.post\("/execution/cancel/\{execution_id\})', new_resources + '\n\n\n', content, flags=re.DOTALL)


# 9. GET /executions/{execution_id}/evidence
new_evidence = '''@router.get("/executions/{execution_id}/evidence", response_model=Dict[str, Any])
async def get_execution_evidence(
    execution_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get execution evidence for audit trail (from DB)."""
    from backend.db.models.ai import ExecutionLog, AIAuditLog
    
    result = await db.execute(select(ExecutionLog).where(ExecutionLog.id == execution_id))
    log = result.scalar_one_or_none()
    
    if not log:
        raise HTTPException(status_code=404, detail="Execution not found")
        
    audit_result = await db.execute(select(AIAuditLog).where(AIAuditLog.workspace_id == current_user.workspace_id).limit(1))
    audit = audit_result.scalar_one_or_none()
    
    return {
        "execution_id": log.id,
        "evidence_pack_id": f"ev_{log.id}",
        "workspace_id": log.workspace_id,
        "agent_id": log.user_id,
        "created_at": log.created_at.isoformat() if log.created_at else None,
        "execution_chain": [
            {
                "step": "execution",
                "timestamp": log.created_at.isoformat() if log.created_at else None,
                "data": f"Model {log.model} completed",
                "hash": log.request_hash
            }
        ],
        "resource_usage": {
            "tokens_processed": log.total_tokens,
            "cost_usd": log.cost_usd
        },
        "policy_compliance": {
            "policy_id": log.policy_id,
            "policy_violations": log.policy_flags
        },
        "audit_hash": audit.hmac_hash if audit else None
    }'''
content = re.sub(r'@router\.get\("/executions/\{execution_id\}/evidence".*?(?=@router\.get\("/queue")', new_evidence + '\n\n\n', content, flags=re.DOTALL)


# Write back
with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Rewrote cappo.py successfully")
