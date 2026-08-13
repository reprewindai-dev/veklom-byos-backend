"""Runtime surfaces consumed by the Capability OS.

These routes intentionally expose existing backend capabilities without
manufacturing frontend state. Values are derived from persisted runtime data.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database.database import get_db
from backend.core.security.auth import get_current_admin, get_current_user
from backend.db.models.ai import ExecutionLog
from backend.db.models.billing import WalletTransaction
from backend.db.models.run import VeklomRun
from backend.db.models.security import KillSwitchState
from backend.db.models.workspace import Workspace

router = APIRouter(tags=["Runtime Surface"])


class KillSwitchActivation(BaseModel):
    reason: str | None = None


@router.get("/platform/pulse")
async def platform_pulse(db: AsyncSession = Depends(get_db)):
    """Return real platform pulse values from persisted runtime state."""
    now = datetime.now(timezone.utc)
    since = now - timedelta(minutes=5)

    traffic = (
        await db.execute(
            select(
                func.count(ExecutionLog.id),
                func.coalesce(func.avg(ExecutionLog.latency_ms), 0.0),
                func.coalesce(
                    func.sum(case((ExecutionLog.status != "completed", 1), else_=0)),
                    0,
                ),
            ).where(ExecutionLog.created_at >= since)
        )
    ).first()

    sample_count = int((traffic[0] if traffic else 0) or 0)
    avg_latency_ms = float((traffic[1] if traffic else 0.0) or 0.0)
    error_count = int((traffic[2] if traffic else 0) or 0)

    async def count_model(model) -> int:
        return int((await db.scalar(select(func.count()).select_from(model))) or 0)

    total_workspaces = await count_model(Workspace)
    governed_runs = await count_model(VeklomRun)
    executions_total = await count_model(ExecutionLog)

    return {
        "latency_ms": round(avg_latency_ms, 1),
        "throughput_req_sec": round(sample_count / 300.0, 4),
        "error_rate_pct": round((error_count / sample_count) * 100.0, 3) if sample_count else 0.0,
        "samples_5m": sample_count,
        "total_workspaces": total_workspaces,
        "governed_runs_total": governed_runs,
        "executions_total": executions_total,
        "source": "execution_logs+workspace+veklom_runs",
        "simulated": False,
        "observed_at": now.isoformat(),
    }


@router.get("/wallet/balance")
async def wallet_balance(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the authenticated workspace's persisted operating reserve."""
    workspace_id = user.workspace_id or ""
    topups = await db.scalar(
        select(func.coalesce(func.sum(WalletTransaction.amount), 0.0)).where(
            WalletTransaction.workspace_id == workspace_id,
            WalletTransaction.tx_type.in_(["topup", "activation", "credit"]),
        )
    ) or 0.0
    debits = await db.scalar(
        select(func.coalesce(func.sum(WalletTransaction.amount), 0.0)).where(
            WalletTransaction.workspace_id == workspace_id,
            WalletTransaction.tx_type == "debit",
        )
    ) or 0.0
    balance = max(round(float(topups) - abs(float(debits)), 4), 0.0)
    return {
        "balance_usd": balance,
        "currency": "USD",
        "total_credits": round(float(topups), 4),
        "total_debits": round(abs(float(debits)), 4),
        "source": "wallet_transactions",
        "simulated": False,
    }


@router.get("/kill-switch/status")
async def kill_switch_status(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    workspace_id = user.workspace_id or ""
    state = (
        await db.execute(
            select(KillSwitchState).where(KillSwitchState.workspace_id == workspace_id)
        )
    ).scalar_one_or_none()

    if state is None:
        return {
            "is_active": False,
            "workspace_id": workspace_id,
            "source": "kill_switch_states",
            "simulated": False,
        }

    return {
        "is_active": bool(state.is_active),
        "workspace_id": workspace_id,
        "activated_by": state.activated_by or None,
        "reason": state.reason or None,
        "activated_at": state.activated_at.isoformat() if state.activated_at else None,
        "deactivated_at": state.deactivated_at.isoformat() if state.deactivated_at else None,
        "source": "kill_switch_states",
        "simulated": False,
    }


@router.post("/kill-switch/activate")
async def activate_kill_switch(
    body: KillSwitchActivation,
    user=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    workspace_id = user.workspace_id or ""
    state = (
        await db.execute(
            select(KillSwitchState).where(KillSwitchState.workspace_id == workspace_id)
        )
    ).scalar_one_or_none()
    now = datetime.now(timezone.utc)

    if state is None:
        state = KillSwitchState(workspace_id=workspace_id)
        db.add(state)

    state.is_active = True
    state.activated_by = user.id
    state.reason = (body.reason or "Manual halt from Capability OS").strip()
    state.activated_at = now
    state.deactivated_at = None
    await db.commit()

    return {
        "is_active": True,
        "workspace_id": workspace_id,
        "activated_by": user.id,
        "reason": state.reason,
        "activated_at": now.isoformat(),
        "source": "kill_switch_states",
        "simulated": False,
    }


@router.post("/kill-switch/deactivate")
async def deactivate_kill_switch(
    user=Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    workspace_id = user.workspace_id or ""
    state = (
        await db.execute(
            select(KillSwitchState).where(KillSwitchState.workspace_id == workspace_id)
        )
    ).scalar_one_or_none()
    now = datetime.now(timezone.utc)

    if state is not None:
        state.is_active = False
        state.deactivated_at = now
        await db.commit()

    return {
        "is_active": False,
        "workspace_id": workspace_id,
        "deactivated_by": user.id,
        "deactivated_at": now.isoformat(),
        "source": "kill_switch_states",
        "simulated": False,
    }
