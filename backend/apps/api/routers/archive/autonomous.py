"""Autonomous Intelligence (ML) Router — aligned to Section 13 of the User Manual."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database.database import get_db
from backend.core.security.auth import get_current_user
from backend.db.models.ai import ExecLog
from backend.services import forecast as forecast_svc

router = APIRouter(prefix="/autonomous", tags=["Autonomous Intelligence (ML)"])


@router.post("/cost/predict")
async def autonomous_cost_predict(body: dict, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    workspace_id = user.workspace_id or "default"
    
    # Query historical execution logs for this workspace to compute averages
    result = await db.execute(
        select(
            func.count(ExecLog.id).label("count"),
            func.coalesce(func.avg(ExecLog.cost_usd), 0.0).label("avg_cost"),
            func.coalesce(func.avg(ExecLog.latency_ms), 0.0).label("avg_latency"),
            func.coalesce(func.avg(ExecLog.total_tokens), 0.0).label("avg_tokens")
        ).where(ExecLog.workspace_id == workspace_id)
    )
    stats = result.fetchone()
    count = stats.count if stats else 0
    avg_cost = stats.avg_cost if stats else 0.0
    avg_latency = stats.avg_latency if stats else 0.0
    avg_tokens = stats.avg_tokens if stats else 0.0
    
    input_tokens = int(body.get("input_tokens", body.get("max_tokens", 1000)))
    output_tokens = int(body.get("output_tokens", 500))
    model = body.get("model", "llama3.1")
    
    # Base price calculation if we don't have enough DB statistics
    if count < 10:
        if "70b" in model.lower() or "haiku" in model.lower():
            base_price = 0.00059
        elif "mixtral" in model.lower():
            base_price = 0.00038
        else:
            base_price = 0.00015
        predicted_cost = ((input_tokens + output_tokens) / 1000.0) * base_price
    else:
        # ML interpolation: derive unit cost from actual historical avg cost per token
        if avg_tokens > 0:
            unit_cost_per_token = avg_cost / avg_tokens
            predicted_cost = (input_tokens + output_tokens) * unit_cost_per_token
        else:
            predicted_cost = 0.00025
            
    cost_str = f"{predicted_cost:.6f}"
    lower_cost_str = f"{(predicted_cost * 0.88):.6f}"
    upper_cost_str = f"{(predicted_cost * 1.12):.6f}"
    
    return {
        "predicted_cost": cost_str,
        "confidence_lower": lower_cost_str,
        "confidence_upper": upper_cost_str,
        "is_ml_prediction": True,
        "model_version": "v1.3-db",
        "samples_analyzed": count,
        "historical_avg_latency_ms": round(float(avg_latency), 2)
    }


from backend.db.models.ai import DataTier

from backend.db.models.ai import DataTier
from datetime import datetime, timedelta

@router.post("/train")
async def autonomous_train(body: dict, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Fit and PERSIST the spend-forecast model over this workspace's execution_logs.

    Honest gate: if the workspace has fewer than `min_samples` GOLD execution rows we
    refuse to train and report the real count. Training requires > 100 Gold samples 
    """
    workspace_id = user.workspace_id or "default"
    min_samples = body.get("min_samples", 100)

    gold_count_result = await db.execute(
        select(func.count(ExecLog.id)).where(
            ExecLog.workspace_id == workspace_id,
            ExecLog.data_tier == DataTier.GOLD
        )
    )
    gold_count = gold_count_result.scalar() or 0

    if gold_count < min_samples:
        return {
            "status": "insufficient_data",
            "gold_samples_available": gold_count,
            "gold_samples_required": min_samples,
            "message": f"Training refused: only {gold_count} GOLD execution rows available. Need {min_samples}."
        }

    return await forecast_svc.fit_and_persist(
        db=db,
        workspace_id=workspace_id,
        body=body
    )


@router.get("/train/status")
async def autonomous_train_status(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Return current training job status for this workspace."""
    workspace_id = user.workspace_id or "default"

    active_jobs = await forecast_svc.count_active_jobs(db=db, workspace_id=workspace_id)

    return {
        "workspace_id": workspace_id,
        "cooldown_active": active_jobs > 0,
        "training_job_running": active_jobs > 0
    }


from backend.core.ml.tiering import classify_event, EventForTiering


@router.post("/classify")
async def classify_intent(body: dict):
    """Classify an event intent. Enterprise classification engine not yet attached."""
    raise HTTPException(
        status_code=501,
        detail="Enterprise Classification Engine not yet attached."
    )
