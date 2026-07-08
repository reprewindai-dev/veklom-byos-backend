"""Spend forecasting service — the Insights/Forecast heart.

Single source of truth for spend projection across the platform.  Fits an
EWMA + linear-trend model over the `execution_logs` cost time series and
persists the coefficients to `forecast_models` so every surface
(Insights, Billing, Workspace overview) reads ONE reproducible, explainable
forecast instead of three independent `value * 30` guesses.

Honesty contract: when there is not enough history the service returns
`method="insufficient_data"` with the real sample count and `confidence=0.0`
so the UI shows an honest low-confidence / empty state rather than a fake
number.  No value is fabricated.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.ml.tier_types import DataTier
from backend.db.models.ai import ExecutionLog, ForecastModel

DEFAULT_WINDOW_DAYS = 30
EWMA_ALPHA = 0.3
MIN_SAMPLES = 10          # below this we refuse to project (honest empty state)
MIN_DAYS_FOR_TREND = 3    # below this we use level-only (no slope)
MODEL_VERSION = "v1"


# ---------------------------------------------------------------------------
# Pure math (no DB, easy to unit-test)
# ---------------------------------------------------------------------------
def _ewma(values: list[float], alpha: float = EWMA_ALPHA) -> float:
    if not values:
        return 0.0
    level = values[0]
    for v in values[1:]:
        level = alpha * v + (1 - alpha) * level
    return level


def _linear_slope(values: list[float]) -> tuple[float, float]:
    """Least-squares slope/intercept over (index, value).  Returns (slope, intercept)."""
    n = len(values)
    if n < MIN_DAYS_FOR_TREND:
        return 0.0, (values[-1] if values else 0.0)
    xs = list(range(n))
    mx = sum(xs) / n
    my = sum(values) / n
    denom = sum((x - mx) ** 2 for x in xs)
    if denom == 0:
        return 0.0, my
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, values)) / denom
    intercept = my - slope * mx
    return slope, intercept


def _stddev(values: list[float]) -> float:
    n = len(values)
    if n < 2:
        return 0.0
    mean = sum(values) / n
    return (sum((v - mean) ** 2 for v in values) / n) ** 0.5


def _confidence(sample_count: int, daily: list[float]) -> float:
    """Confidence in [0, 0.95] from sample volume and stability.

    More samples + lower relative volatility => higher confidence.  Never
    returns a falsely perfect 1.0.
    """
    if sample_count < MIN_SAMPLES:
        return 0.0
    mean = sum(daily) / len(daily) if daily else 0.0
    cv = (_stddev(daily) / mean) if mean > 0 else 1.0          # coefficient of variation
    stability = max(0.0, 1.0 - min(cv, 1.0))                    # 1 = perfectly stable
    volume = min(1.0, sample_count / 200.0)                     # saturates at 200 samples
    return round(min(0.95, 0.4 * volume + 0.55 * stability), 4)


def project_total(params: dict[str, Any], horizon_days: int) -> float:
    """Project cumulative spend over the next `horizon_days` from fitted params."""
    if not params or params.get("method") == "insufficient_data":
        return 0.0
    level = float(params.get("ewma", params.get("daily_avg", 0.0)))
    slope = float(params.get("slope", 0.0))
    total = 0.0
    for k in range(1, horizon_days + 1):
        total += max(0.0, level + slope * k)
    return round(total, 6)


# ---------------------------------------------------------------------------
# DB-backed fit / persist / read
# ---------------------------------------------------------------------------
async def _daily_series(
    db: AsyncSession,
    workspace_id: str,
    window_days: int = DEFAULT_WINDOW_DAYS,
    locked_execution_log_ids: list[str] | None = None,
    require_locked_gold: bool = False,
) -> tuple[list[float], int, datetime | None]:
    """Return (per-day cost list over the active span, total sample count, first_ts).

    Days are bucketed in Python so the logic is dialect-agnostic (Postgres in
    prod, SQLite fallback in dev).  Internal zero-spend days are real zeros and
    are kept; we do NOT pad leading zeros from before the workspace had any
    activity (that would dilute the average dishonestly).

    Training invariant: when locked_execution_log_ids are provided, this query
    only reads those explicitly locked Gold execution logs. This prevents the
    training path from silently mixing Bronze, Silver, unrated, failed, or
    unlocked rows into the fitted model.
    """
    if require_locked_gold and not locked_execution_log_ids:
        return [], 0, None

    now = datetime.now(timezone.utc)
    start = now - timedelta(days=window_days)

    stmt = select(ExecutionLog.created_at, ExecutionLog.cost).where(
        ExecutionLog.workspace_id == workspace_id,
        ExecutionLog.created_at >= start,
    )

    if locked_execution_log_ids is not None:
        stmt = stmt.where(
            ExecutionLog.id.in_(locked_execution_log_ids),
            ExecutionLog.data_tier == DataTier.gold,
            ExecutionLog.eligible_for_training.is_(True),
            ExecutionLog.training_locked_at.is_not(None),
        )

    rows = (await db.execute(stmt)).all()

    sample_count = len(rows)
    if sample_count == 0:
        return [], 0, None

    buckets: dict[str, float] = {}
    first_ts: datetime | None = None
    for created_at, cost in rows:
        if created_at is None:
            continue
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        if first_ts is None or created_at < first_ts:
            first_ts = created_at
        day = created_at.date().isoformat()
        buckets[day] = buckets.get(day, 0.0) + float(cost or 0.0)

    if first_ts is None:
        return [], sample_count, None

    span_days = (now.date() - first_ts.date()).days + 1
    span_days = max(1, min(span_days, window_days))
    series = [
        buckets.get((now - timedelta(days=span_days - 1 - i)).date().isoformat(), 0.0)
        for i in range(span_days)
    ]
    return series, sample_count, first_ts


def _fit(daily: list[float], sample_count: int) -> dict[str, Any]:
    if sample_count < MIN_SAMPLES or not daily:
        return {
            "method": "insufficient_data",
            "daily_avg": round(sum(daily) / len(daily), 6) if daily else 0.0,
            "ewma": 0.0,
            "slope": 0.0,
            "intercept": 0.0,
            "stddev": 0.0,
            "sample_count": sample_count,
            "active_days": len(daily),
            "min_samples": MIN_SAMPLES,
        }
    slope, intercept = _linear_slope(daily)
    return {
        "method": "ewma_linear",
        "daily_avg": round(sum(daily) / len(daily), 6),
        "ewma": round(_ewma(daily), 6),
        "slope": round(slope, 6),
        "intercept": round(intercept, 6),
        "stddev": round(_stddev(daily), 6),
        "sample_count": sample_count,
        "active_days": len(daily),
        "min_samples": MIN_SAMPLES,
    }


async def train_and_persist(
    db: AsyncSession,
    workspace_id: str,
    window_days: int = DEFAULT_WINDOW_DAYS,
    locked_execution_log_ids: list[str] | None = None,
    require_locked_gold: bool = False,
) -> dict[str, Any]:
    """Fit the spend model and upsert the persisted row.  Returns the record.

    If require_locked_gold=True, the service refuses to train from the broad
    workspace history and only uses explicitly locked Gold execution logs.
    """
    daily, sample_count, _ = await _daily_series(
        db,
        workspace_id,
        window_days,
        locked_execution_log_ids=locked_execution_log_ids,
        require_locked_gold=require_locked_gold,
    )

    if require_locked_gold and sample_count == 0:
        return {
            "trained": False,
            "method": "no_valid_locked_gold_records",
            "samples_used": 0,
            "confidence": 0.0,
            "params": {
                "method": "no_valid_locked_gold_records",
                "sample_count": 0,
                "min_samples": MIN_SAMPLES,
            },
            "model_version": MODEL_VERSION,
            "trained_at": None,
        }

    params = _fit(daily, sample_count)
    confidence = _confidence(sample_count, daily)

    existing = (
        await db.execute(
            select(ForecastModel).where(
                ForecastModel.workspace_id == workspace_id,
                ForecastModel.model_type == "spend",
            )
        )
    ).scalar_one_or_none()

    if existing:
        existing.method = params["method"]
        existing.params = params
        existing.samples_used = sample_count
        existing.confidence = confidence
        existing.window_days = window_days
        existing.version = MODEL_VERSION
        existing.trained_at = datetime.now(timezone.utc)
        record = existing
    else:
        record = ForecastModel(
            workspace_id=workspace_id,
            model_type="spend",
            method=params["method"],
            params=params,
            samples_used=sample_count,
            confidence=confidence,
            window_days=window_days,
            version=MODEL_VERSION,
        )
        db.add(record)

    await db.commit()
    await db.refresh(record)
    return {
        "trained": params["method"] != "insufficient_data",
        "method": record.method,
        "samples_used": record.samples_used,
        "confidence": record.confidence,
        "params": record.params,
        "model_version": record.version,
        "trained_at": record.trained_at.isoformat() if record.trained_at else None,
    }


async def get_projection(
    db: AsyncSession, workspace_id: str, horizon_days: int = 30
) -> dict[str, Any]:
    """Canonical spend projection.  Uses the persisted model when present;
    otherwise fits on the fly (without persisting) so reads always work.
    """
    record = (
        await db.execute(
            select(ForecastModel).where(
                ForecastModel.workspace_id == workspace_id,
                ForecastModel.model_type == "spend",
            )
        )
    ).scalar_one_or_none()

    if record and record.params:
        params = record.params
        confidence = record.confidence
        sample_count = record.samples_used
        persisted = True
        trained_at = record.trained_at.isoformat() if record.trained_at else None
    else:
        daily, sample_count, _ = await _daily_series(db, workspace_id)
        params = _fit(daily, sample_count)
        confidence = _confidence(sample_count, daily)
        persisted = False
        trained_at = None

    projected = project_total(params, horizon_days)
    return {
        "workspace_id": workspace_id,
        "horizon_days": horizon_days,
        "projected_spend_usd": projected,
        "method": params.get("method", "insufficient_data"),
        "confidence": confidence,
        "samples_used": sample_count,
        "daily_avg_usd": params.get("daily_avg", 0.0),
        "trend_slope_usd_per_day": params.get("slope", 0.0),
        "persisted_model": persisted,
        "trained_at": trained_at,
        "model_version": MODEL_VERSION,
    }
