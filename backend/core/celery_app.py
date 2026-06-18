"""Celery Application Setup with Redis Broker and Beat Scheduling."""

import os
from celery import Celery
from celery.schedules import crontab

# Configure Celery
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "veklom_tasks",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["backend.core.tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,
)

# Celery Beat Schedule
celery_app.conf.beat_schedule = {
    # 1. Train ML models nightly at 2:00 AM UTC
    "retrain-ml-models-nightly": {
        "task": "backend.core.tasks.train_forecast_models_task",
        "schedule": crontab(hour=2, minute=0),
    },
    # 2. Check budget limits every hour
    "check-budget-limits-hourly": {
        "task": "backend.core.tasks.check_workspace_budgets_task",
        "schedule": crontab(minute=0),
    },
    # 3. Purge retained data every day at 3:00 AM UTC
    "purge-expired-data-daily": {
        "task": "backend.core.tasks.purge_expired_logs_task",
        "schedule": crontab(hour=3, minute=0),
        "args": (90,)  # Default to 90 days retention if not specified per workspace
    },
}
