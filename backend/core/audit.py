import logging
import uuid
import hashlib
import json
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy import select
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
    Computes a cryptographic hash chain to ensure the integrity of the audit log.
    """
    if details is None:
        details = {}
        
    # Get the previous hash chain for this workspace (or generally if workspace_id is empty)
    try:
        stmt = select(AuditLog.hash_chain).where(
            AuditLog.workspace_id == workspace_id
        ).order_by(AuditLog.created_at.desc()).limit(1)
        res = await db.execute(stmt)
        prev_hash = res.scalar_one_or_none() or ""
    except Exception as e:
        logger.warning(f"Could not fetch previous hash chain for workspace {workspace_id}: {e}")
        prev_hash = ""

    # Sort keys for deterministic JSON serialization
    details_str = json.dumps(details, sort_keys=True, default=str)
    
    # Construct block contents to hash
    event_data = f"{action}:{user_id}:{workspace_id}:{resource_type}:{resource_id}:{details_str}:{prev_hash}"
    hash_chain = hashlib.sha256(event_data.encode("utf-8")).hexdigest()

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
        prev_hash=prev_hash,
        hash_chain=hash_chain,
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

