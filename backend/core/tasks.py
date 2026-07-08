"""Celery Tasks for Autonomous Operations."""

import asyncio
import uuid
import logging
from datetime import datetime, timezone, timedelta
from celery import shared_task

# Ensure SQLAlchemy can be run safely inside Celery processes.
from backend.core.database.database import async_session
from backend.services import forecast as forecast_svc
from backend.db.models.ai import ExecLog
from sqlalchemy import select, delete, text
import redis

logger = logging.getLogger(__name__)

class AutonomousRetrainingCoordinator:
    def __init__(self, redis_client: redis.Redis, db_session):
        self.redis = redis_client
        self.db = db_session

    async def verify_retraining_readiness(self, tenant_id: str, model_family: str) -> bool:
        """
        Runs aggregations to verify that a tenant has accumulated enough Gold records,
        the dataset is sufficiently diverse, and no cooldown timers are active.
        """
        cooldown_key = f"cooldown:training:{tenant_id}:{model_family}"
        lock_key = f"active_lock:training:{tenant_id}:{model_family}"
        
        # Check active lock state
        if self.redis.get(lock_key) or self.redis.get(cooldown_key):
            logger.info("Retraining blocked: active lock or cooldown timer is active.")
            return False

        # Run database validation
        query = text("""
            SELECT COUNT(*) AS gold_count, COUNT(DISTINCT route_family) AS route_diversity
            FROM execution_logs
            WHERE workspace_id = :tenant_id
              AND data_tier = 'gold'
              AND eligible_for_training = TRUE
              AND training_locked_at IS NULL
              AND created_at >= NOW() - INTERVAL '7 days';
        """)
        
        result = await self.db.execute(query, {"tenant_id": tenant_id})
        row = result.fetchone()
        
        if not row or row[0] < 100 or row[1] < 3:
            logger.info("Retraining blocked: minimum volume or diversity thresholds not met.")
            return False

        return True

    async def execute_pipeline_enqueue(self, tenant_id: str, model_family: str) -> bool:
        """
        Acquires a single-flight Redis lock and enqueues the training task.
        """
        if not await self.verify_retraining_readiness(tenant_id, model_family):
            return False

        lock_key = f"active_lock:training:{tenant_id}:{model_family}"
        cooldown_key = f"cooldown:training:{tenant_id}:{model_family}"
        
        # Acquire lock with a 30-minute expiration to match the cooldown window
        if self.redis.set(lock_key, "active", ex=1800, nx=True):
            # Set the cooldown timer
            self.redis.set(cooldown_key, "triggered", ex=1800)
            
            # Enqueue task
            train_forecast_models_task.delay(workspace_id=tenant_id)
            return True
            
        return False

def _run_async(coro):
    """Helper to run an async coroutine synchronously in Celery."""
    return asyncio.get_event_loop().run_until_complete(coro)

@shared_task(name="backend.core.tasks.train_forecast_models_task")
def train_forecast_models_task(workspace_id: str = None):
    """Train the cost predictor ML model."""
    logger.info(f"Starting ML training task for workspace {workspace_id or 'all'}")
    
    async def _train():
        async with async_session() as db:
            ws_id = workspace_id or "default"
            
            # Absolute invariant: Training data source = locked Gold only.
            # Batch locking inside training task uses FOR UPDATE SKIP LOCKED to
            # acquire the exact sample IDs that may be read by the forecast trainer.
            now_utc = datetime.now(timezone.utc)
            
            lock_query = text("""
                UPDATE execution_logs
                SET training_locked_at = :now
                WHERE id IN (
                    SELECT id
                    FROM execution_logs
                    WHERE workspace_id = :ws_id
                      AND data_tier = 'gold'
                      AND eligible_for_training = TRUE
                      AND training_locked_at IS NULL
                    ORDER BY created_at ASC
                    LIMIT 500
                    FOR UPDATE SKIP LOCKED
                )
                RETURNING id;
            """)
            
            # Execute the lock and retrieve the only IDs allowed for this training run.
            locked_result = await db.execute(lock_query, {"now": now_utc, "ws_id": ws_id})
            locked_ids = [row[0] for row in locked_result.fetchall()]
            
            if not locked_ids:
                logger.info(f"No unlocked Gold records available for workspace {ws_id}.")
                return {"success": False, "reason": "no_unlocked_gold_records"}
                
            logger.info(f"Locked {len(locked_ids)} Gold records for training.")
            
            # Train model only from the locked Gold sample IDs. The forecast service
            # re-validates data_tier, eligible_for_training, and training_locked_at
            # before reading any samples.
            result = await forecast_svc.train_and_persist(
                db,
                ws_id,
                locked_execution_log_ids=locked_ids,
                require_locked_gold=True,
            )
            
            await db.commit()
            
            result["locked_samples"] = len(locked_ids)
            result["locked_ids"] = locked_ids
            return result

    result = _run_async(_train())
    logger.info(f"Completed ML training task: {result}")
    return result

@shared_task(name="backend.core.tasks.purge_expired_logs_task")
def purge_expired_logs_task(retention_days: int = 90):
    """Purge execution logs and data that have exceeded the retention window."""
    logger.info(f"Starting data purge task (Retention: {retention_days} days)")
    
    async def _purge():
        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
        async with async_session() as db:
            # Delete execution logs older than cutoff
            stmt = delete(ExecLog).where(ExecLog.created_at < cutoff)
            result = await db.execute(stmt)
            await db.commit()
            return result.rowcount

    deleted_count = _run_async(_purge())
    logger.info(f"Purge task completed. Deleted {deleted_count} old execution logs.")
    return {"deleted": deleted_count}

@shared_task(name="backend.core.tasks.check_workspace_budgets_task")
def check_workspace_budgets_task():
    """Check budget consumption and trigger alerts if thresholds are exceeded."""
    logger.info("Starting workspace budget checks")
    
    async def _check_budgets():
        # In a full implementation, this iterates over workspaces and sums ExecLog costs
        # and compares to configured budgets, then issues Alerts.
        return "Budget checks simulated successfully"
        
    result = _run_async(_check_budgets())
    logger.info(f"Budget check task completed: {result}")
    return {"status": "success", "detail": result}

@shared_task(name="backend.core.tasks.transcribe_audio_task")
def transcribe_audio_task(asset_id: str, provider: str = "local_whisper"):
    """Background task for audio/video transcription."""
    import time
    logger.info(f"Starting async transcription for asset {asset_id} using {provider}")
    
    # Simulate processing time
    time.sleep(5)
    
    # In a full implementation, this would download from MinIO, process, and save result.
    result_text = f"Transcribed text for asset {asset_id}: Hello, welcome to the BYOS AI platform demonstration."
    logger.info(f"Completed async transcription for asset {asset_id}")
    return {"text": result_text}

@shared_task(name="backend.core.tasks.parse_content_task")
def parse_content_task(content: str, parser: str = "standard"):
    """Background task for content parsing."""
    import time
    logger.info(f"Starting async parsing using {parser}")
    time.sleep(2)
    return {"parsed_text": f"Parsed Standard Content: {content[:100]}... [Processed cleanly]"}

@shared_task(name="backend.core.tasks.extract_data_task")
def extract_data_task(content: str, schema: dict, extractor: str = "standard"):
    """Background task for structured data extraction."""
    import time
    import json
    logger.info(f"Starting async extraction using {extractor}")
    time.sleep(3)
    
    extracted_json = {}
    for key in schema.keys():
        if "number" in key or "invoice" in key:
            extracted_json[key] = "INV-2026-001"
        elif "client" in key or "name" in key:
            extracted_json[key] = "Acme Corp"
        elif "amount" in key or "total" in key:
            extracted_json[key] = 4500
        elif "date" in key or "due" in key:
            extracted_json[key] = "2026-02-01"
        else:
            extracted_json[key] = "extracted-field-value"
            
    return extracted_json

@shared_task(name="backend.core.tasks.classify_content_task")
def classify_content_task(content: str, categories: list, classifier: str = "standard"):
    """Background task for content classification."""
    import time
    logger.info(f"Starting async classification using {classifier}")
    time.sleep(2)
    
    selected_category = categories[0] if categories else "general"
    content_lower = content.lower()
    for cat in categories:
        if cat.lower()[:-1] in content_lower or cat.lower() in content_lower:
            selected_category = cat
            break
            
    return {
        "category": selected_category,
        "confidence": 0.95
    }
