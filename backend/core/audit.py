import logging
import uuid
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from backend.db.models.security import AuditLog

logger = logging.getLogger(__name__)

async def log_audit_event(
    db: AsyncSession,
    user_id: str,
    action: str,
    workspace_id: str = "",
    resource_type: str = "",
    resource_id: str = "",
    details: Optional[Dict[str, Any]] = None,
    ip_address: str = "",
    user_agent: str = ""
) -> AuditLog:
    """
    Logs an audit event to the database for security and compliance tracking.
    """
    if details is None:
        details = {}
        
    audit_entry = AuditLog(
        id=str(uuid.uuid4()),
        user_id=user_id,
        workspace_id=workspace_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        ip_address=ip_address,
        user_agent=user_agent,
        created_at=datetime.now(timezone.utc)
    )
    
    db.add(audit_entry)
    try:
        await db.commit()
        await db.refresh(audit_entry)
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to record audit log {action} for user {user_id}: {e}")
        
    return audit_entry
