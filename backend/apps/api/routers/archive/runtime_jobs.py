import json
import logging
from datetime import datetime, timezone
from typing import Optional, Literal
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from redis.asyncio import Redis

from backend.core.database.redis_client import get_redis

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/runtime/jobs", tags=["Runtime Jobs"])

class JobStatusResponse(BaseModel):
    transaction_id: str
    status: Literal["PENDING", "PROCESSING", "COMPLETED", "FAILED", "EXPIRED", "REVIEW_REQUIRED", "UNKNOWN", "NOT_WIRED"]
    destination_node: Optional[str] = None
    progress: int = 0
    detail: str
    proof_hash: Optional[str] = None
    result_ref: Optional[str] = None
    updated_at: str

@router.get("/{transaction_id}/status", response_model=JobStatusResponse)
async def get_job_status(transaction_id: str, redis_client: Redis = Depends(get_redis)):
    """
    Polls the runtime job status from Redis for idempotency and tracking.
    """
    if not redis_client:
        logger.error("Redis client is not available")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Job status tracking is currently unavailable."
        )

    try:
        key = f"job:{transaction_id}"
        state_str = await redis_client.get(key)
        
        if not state_str:
            return JobStatusResponse(
                transaction_id=transaction_id,
                status="UNKNOWN",
                detail="No active transaction state found. It may have expired or never existed.",
                updated_at=datetime.now(timezone.utc).isoformat()
            )
            
        try:
            state_data = json.loads(state_str)
        except json.JSONDecodeError:
            # Fallback if state is not JSON
            logger.warning(f"Failed to parse job state as JSON for {transaction_id}. Value: {state_str}")
            return JobStatusResponse(
                transaction_id=transaction_id,
                status="UNKNOWN",
                detail="State data was malformed.",
                updated_at=datetime.now(timezone.utc).isoformat()
            )
            
        # Parse dynamic fields from JSON
        status_val = state_data.get("status", "UNKNOWN")
        valid_statuses = {"PENDING", "PROCESSING", "COMPLETED", "FAILED", "EXPIRED", "REVIEW_REQUIRED", "UNKNOWN", "NOT_WIRED"}
        if status_val not in valid_statuses:
            status_val = "UNKNOWN"
            
        return JobStatusResponse(
            transaction_id=transaction_id,
            status=status_val,
            destination_node=state_data.get("destination_node"),
            progress=state_data.get("progress", 0),
            detail=state_data.get("detail", "Processing transaction..."),
            proof_hash=state_data.get("proof_hash"),
            result_ref=state_data.get("result_ref"),
            updated_at=state_data.get("updated_at", datetime.now(timezone.utc).isoformat())
        )
        
    except Exception as e:
        logger.error(f"Error retrieving job status from Redis for {transaction_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to query job status due to a backend error."
        )
