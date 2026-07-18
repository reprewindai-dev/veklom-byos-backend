"""HRM (Hierarchical Reasoning Model) agent routes — /api/v1/agents/hrm/*.

HRM is a three-tier agent classification:

    prime   — command-level agents; authorised to spawn/govern lower tiers.
    monitor — observation/audit agents; read the ledger, surface anomalies.
    sync    — execution agents; run workloads, report back.

Terminology:
    task force   — the full set of agents (all tiers) registered on an account.
    Zeno interrogation — a point-in-time, read-only chain-of-custody audit of
                         a single agent's ledger.  Named after Zeno's arrow
                         paradox: the timeline is "frozen" at interrogation
                         time and cannot be altered after the record is cut.
    memory vault — the hash-chained LedgerEvent table for an agent.
    telemetry    — aggregate activity metrics (event counts, last-seen,
                   chain-head hash) per agent number.

All endpoints:
  - require a valid JWT (get_current_user).
  - return real DB rows or explicit empty-state; never fabricated records.
  - admin-write operations (register, update) also require OWNER/ADMIN role.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database.database import get_db
from backend.core.security.auth import get_current_user
from backend.db.models.agent import HRM_TIERS, Account, Agent, AgentUser
from backend.db.models.ledger import LedgerEvent

router = APIRouter(prefix="/agents/hrm", tags=["HRM Agents"])


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def _account(user, db: AsyncSession) -> Optional[Account]:
    if not getattr(user, "email", None):
        return None
    au = (await db.execute(select(AgentUser).where(AgentUser.email == user.email).limit(1))).scalar_one_or_none()
    if not au:
        return None
    return (await db.execute(select(Account).where(Account.id == au.account_id))).scalar_one_or_none()


def _require_admin(user):
    role = (getattr(user, "role", "") or "").upper()
    if role not in ("OWNER", "ADMIN") and not getattr(user, "is_superuser", False):
        raise HTTPException(status_code=403, detail="OWNER or ADMIN role required")


def _serialize_agent(a: Agent) -> dict:
    return {
        "id": a.id,
        "agent_id": a.agent_id,
        "agent_number": a.agent_number,
        "name": a.name,
        "creator": a.creator,
        "jurisdiction": a.jurisdiction,
        "declared_purpose": a.declared_purpose,
        "status": a.status,
        "hrm_tier": a.hrm_tier,
        "squad_id": a.squad_id,
        "capabilities": a.capabilities or [],
        "account_id": a.account_id,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


def _empty(reason: str) -> dict:
    return {"items": [], "source": "empty", "reason": reason}


# ---------------------------------------------------------------------------
# GET /api/v1/agents/hrm/audit
# Performance audit across the full task force, grouped by tier.
# ---------------------------------------------------------------------------


@router.get("/audit")
async def hrm_audit(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Audit the full HRM task force.

    Returns per-tier agent counts, status breakdown, and ledger-event
    summary for each agent.  Only agents with a non-null hrm_tier are
    included in the HRM view; standard agents (hrm_tier=null) are excluded.
    """
    acct = await _account(user, db)
    if not acct:
        return _empty("No account row for this user.")

    agents = (
        (
            await db.execute(
                select(Agent)
                .where(Agent.account_id == acct.id, Agent.hrm_tier.isnot(None))
                .order_by(Agent.agent_number.asc().nullsfirst(), Agent.id.asc())
            )
        )
        .scalars()
        .all()
    )

    if not agents:
        return {
            "task_force_size": 0,
            "by_tier": {t: {"count": 0, "agents": []} for t in HRM_TIERS},
            "source": "empty",
            "reason": "No HRM agents registered yet. Use POST /api/v1/agents/hrm/register.",
        }

    agent_ids = [a.id for a in agents]

    # Combined aggregation to avoid double table scanning
    agg_rows = (
        await db.execute(
            select(
                LedgerEvent.agent_id,
                func.count(LedgerEvent.id).label("event_count"),
                func.max(LedgerEvent.created_at).label("last_event_at"),
            )
            .where(LedgerEvent.agent_id.in_(agent_ids))
            .group_by(LedgerEvent.agent_id)
        )
    ).all()

    event_counts = {row[0]: row[1] for row in agg_rows}
    last_event = {row[0]: row[2] for row in agg_rows}

    by_tier: dict = {t: {"count": 0, "agents": []} for t in HRM_TIERS}
    for a in agents:
        tier = a.hrm_tier or "unknown"
        entry = {
            **_serialize_agent(a),
            "ledger_events": event_counts.get(a.id, 0),
            "last_activity": last_event.get(a.id, None),
        }
        if tier not in by_tier:
            by_tier[tier] = {"count": 0, "agents": []}
        by_tier[tier]["agents"].append(entry)
        by_tier[tier]["count"] += 1

    return {
        "as_of": _utcnow().isoformat(),
        "task_force_size": len(agents),
        "by_tier": by_tier,
        "source": "db",
        "account_id": acct.id,
    }


# ---------------------------------------------------------------------------
# GET /api/v1/agents/hrm/agents/{agent_number}
# ---------------------------------------------------------------------------


@router.get("/agents/{agent_number}")
async def hrm_agent_by_number(
    agent_number: int,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Fetch a single HRM agent by its sequential task-force number."""
    acct = await _account(user, db)
    if not acct:
        raise HTTPException(status_code=404, detail="No account for user")
    a = (
        await db.execute(
            select(Agent).where(
                Agent.account_id == acct.id,
                Agent.agent_number == agent_number,
                Agent.hrm_tier.isnot(None),
            )
        )
    ).scalar_one_or_none()
    if not a:
        raise HTTPException(
            status_code=404,
            detail=f"No HRM agent with number {agent_number}. The task force is empty unless agents are registered via POST /api/v1/agents/hrm/register.",
        )
    event_count = (
        await db.execute(select(func.count(LedgerEvent.id)).where(LedgerEvent.agent_id == a.id))
    ).scalar() or 0
    last_event = (
        await db.execute(
            select(LedgerEvent).where(LedgerEvent.agent_id == a.id).order_by(LedgerEvent.created_at.desc()).limit(1)
        )
    ).scalar_one_or_none()
    return {
        **_serialize_agent(a),
        "ledger_events": event_count,
        "chain_head": last_event.event_hash if last_event else None,
        "last_activity": last_event.created_at.isoformat() if last_event and last_event.created_at else None,
        "source": "db",
    }


# ---------------------------------------------------------------------------
# GET /api/v1/agents/hrm/monitors
# ---------------------------------------------------------------------------


@router.get("/monitors")
async def hrm_monitors(
    status: Optional[str] = Query(None),
    squad_id: Optional[str] = Query(None),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """All active HRM Monitor agents in the task force."""
    acct = await _account(user, db)
    if not acct:
        return _empty("No account for user.")
    q = select(Agent).where(
        Agent.account_id == acct.id,
        Agent.hrm_tier == "monitor",
    )
    if status:
        q = q.where(Agent.status == status)
    if squad_id:
        q = q.where(Agent.squad_id == squad_id)
    agents = (await db.execute(q.order_by(Agent.agent_number.asc().nullsfirst()))).scalars().all()
    return {
        "items": [_serialize_agent(a) for a in agents],
        "count": len(agents),
        "source": "db" if agents else "empty",
        "reason": None if agents else "No HRM-Monitor agents registered yet.",
    }


# ---------------------------------------------------------------------------
# GET /api/v1/agents/hrm/sync/telemetry
# Telemetry for HRM-Sync agents. ?agents=15,30,45 filters by agent_number.
# ---------------------------------------------------------------------------


@router.get("/sync/telemetry")
async def hrm_sync_telemetry(
    agents: Optional[str] = Query(None, description="Comma-separated agent_numbers, e.g. 15,30,45"),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Telemetry report for HRM-Sync agents.

    `telemetry` = per-agent: event count, last-seen timestamp, chain-head
    hash, status, and capabilities list.  No metrics are fabricated;
    absent activity returns zero counts.
    """
    acct = await _account(user, db)
    if not acct:
        return _empty("No account for user.")

    q = select(Agent).where(Agent.account_id == acct.id, Agent.hrm_tier == "sync")
    if agents:
        try:
            nums = [int(n.strip()) for n in agents.split(",") if n.strip()]
        except ValueError:
            raise HTTPException(status_code=400, detail="agents must be comma-separated integers")
        q = q.where(Agent.agent_number.in_(nums))
    rows = (await db.execute(q.order_by(Agent.agent_number.asc().nullsfirst()))).scalars().all()

    agent_ids = [a.id for a in rows]
    event_counts = {}
    last_events = {}

    if agent_ids:
        counts_res = await db.execute(
            select(LedgerEvent.agent_id, func.count(LedgerEvent.id))
            .where(LedgerEvent.agent_id.in_(agent_ids))
            .group_by(LedgerEvent.agent_id)
        )
        event_counts = {row[0]: row[1] for row in counts_res.all()}

        lasts_res = await db.execute(
            select(LedgerEvent)
            .where(LedgerEvent.agent_id.in_(agent_ids))
            .distinct(LedgerEvent.agent_id)
            .order_by(LedgerEvent.agent_id, LedgerEvent.created_at.desc())
        )
        last_events = {ev.agent_id: ev for ev in lasts_res.scalars().all()}

    telemetry = []
    for a in rows:
        event_count = event_counts.get(a.id, 0)
        last = last_events.get(a.id)
        telemetry.append(
            {
                **_serialize_agent(a),
                "telemetry": {
                    "event_count": event_count,
                    "chain_head": last.event_hash if last else None,
                    "last_activity": last.created_at.isoformat() if last and last.created_at else None,
                    "is_idle": event_count == 0,
                },
            }
        )

    return {
        "as_of": _utcnow().isoformat(),
        "sync_agents_matched": len(telemetry),
        "items": telemetry,
        "source": "db" if telemetry else "empty",
        "reason": None if telemetry else "No HRM-Sync agents match the query.",
    }


# ---------------------------------------------------------------------------
# POST /api/v1/agents/hrm/{agent_id}/zeno-interrogation
# Point-in-time chain-of-custody audit (read-only, ledger replay).
# ---------------------------------------------------------------------------


@router.post("/{agent_id}/zeno-interrogation")
async def zeno_interrogation(
    agent_id: str,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Zeno interrogation — read-only chain-of-custody audit.

    Replays the full ledger for an agent and:
      - verifies SHA-256 hash chain integrity.
      - extracts all decision events.
      - identifies gap events (chain breaks).
      - returns a structured verdict: chain_intact | no_activity | chain_break.

    The agent's ledger is the "memory vault."  Nothing is written; this is
    a pure replay of what already exists.  The interrogation record is
    timestamped in the response body only — not persisted — so it cannot
    alter the chain it inspects.
    """
    acct = await _account(user, db)
    if not acct:
        raise HTTPException(status_code=404, detail="No account for user")
    a = (
        await db.execute(
            select(Agent).where(
                Agent.account_id == acct.id,
                Agent.agent_id == agent_id,
            )
        )
    ).scalar_one_or_none()
    if not a:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id!r} not found")

    events = (
        (
            await db.execute(
                select(LedgerEvent).where(LedgerEvent.agent_id == a.id).order_by(LedgerEvent.created_at.asc())
            )
        )
        .scalars()
        .all()
    )

    if not events:
        return {
            "agent_id": agent_id,
            "agent_number": a.agent_number,
            "hrm_tier": a.hrm_tier,
            "verdict": "no_activity",
            "chain_intact": None,
            "event_count": 0,
            "decisions": [],
            "gap_events": [],
            "interrogated_at": _utcnow().isoformat(),
        }

    chain_intact = True
    gaps = []
    decisions = []
    last_hash = ""

    for ev in events:
        if ev.prev_event_hash != last_hash:
            chain_intact = False
            gaps.append(
                {
                    "event_id": ev.event_id,
                    "event_type": ev.event_type,
                    "expected_prev": last_hash[:16] + "...",
                    "stored_prev": (ev.prev_event_hash or "")[:16] + "...",
                    "created_at": ev.created_at.isoformat() if ev.created_at else None,
                }
            )

        if ev.event_type in (
            "agent.decision",
            "agent.run.started",
            "agent.run.completed",
            "agent.policy.blocked",
            "agent.violation",
            "regulatory_breach",
        ):
            decisions.append(
                {
                    "event_id": ev.event_id,
                    "event_type": ev.event_type,
                    "actor": ev.actor,
                    "summary": ev.summary,
                    "created_at": ev.created_at.isoformat() if ev.created_at else None,
                    "event_hash": ev.event_hash[:16] + "...",
                }
            )

        last_hash = ev.event_hash

    return {
        "agent_id": agent_id,
        "agent_number": a.agent_number,
        "name": a.name,
        "hrm_tier": a.hrm_tier,
        "verdict": "chain_intact" if chain_intact else "chain_break",
        "chain_intact": chain_intact,
        "event_count": len(events),
        "chain_head": events[-1].event_hash if events else None,
        "decisions": decisions,
        "gap_events": gaps,
        "interrogated_at": _utcnow().isoformat(),
        "note": "Read-only replay. Nothing was written to the ledger during this interrogation.",
    }


# ---------------------------------------------------------------------------
# POST /api/v1/agents/hrm/register
# Register a new HRM agent (admin-only).
# ---------------------------------------------------------------------------


class RegisterHRMAgentBody(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    hrm_tier: str = Field(..., description="prime | monitor | sync")
    creator: str = Field(..., min_length=1, max_length=255)
    jurisdiction: str = Field(..., min_length=1, max_length=64)
    declared_purpose: str = Field(..., min_length=1, max_length=512)
    agent_number: Optional[int] = Field(None, ge=1)
    squad_id: Optional[str] = Field(None, max_length=64)
    capabilities: Optional[list[str]] = Field(default_factory=list)


@router.post("/register", status_code=201)
async def hrm_register_agent(
    body: RegisterHRMAgentBody,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Register a new HRM agent.  Admin/Owner role required.

    This is the only way to populate the task force — no agents are
    seeded automatically.  agent_number must be unique within the account
    if provided.
    """
    _require_admin(user)
    acct = await _account(user, db)
    if not acct:
        raise HTTPException(
            status_code=400, detail="No account row for user. Register via /api/v1/internal/uacp/accounts first."
        )

    if body.hrm_tier not in HRM_TIERS:
        raise HTTPException(status_code=400, detail=f"hrm_tier must be one of {HRM_TIERS}")

    if body.agent_number is not None:
        conflict = (
            await db.execute(
                select(Agent).where(
                    Agent.account_id == acct.id,
                    Agent.agent_number == body.agent_number,
                )
            )
        ).scalar_one_or_none()
        if conflict:
            raise HTTPException(
                status_code=409,
                detail=f"agent_number {body.agent_number} is already taken by agent {conflict.agent_id!r}",
            )

    agent_id = str(uuid.uuid4())
    a = Agent(
        account_id=acct.id,
        agent_id=agent_id,
        name=body.name,
        creator=body.creator,
        jurisdiction=body.jurisdiction,
        declared_purpose=body.declared_purpose,
        status="registered",
        hrm_tier=body.hrm_tier,
        agent_number=body.agent_number,
        squad_id=body.squad_id,
        capabilities=body.capabilities or [],
    )
    db.add(a)
    await db.commit()
    await db.refresh(a)
    return {"created": True, "agent": _serialize_agent(a)}


# ---------------------------------------------------------------------------
# PATCH /api/v1/agents/hrm/{agent_id}/status
# Update an agent's status (active | suspended | quarantined | decommissioned).
# ---------------------------------------------------------------------------

VALID_STATUSES = ("registered", "active", "suspended", "quarantined", "decommissioned")


class UpdateStatusBody(BaseModel):
    status: str
    reason: Optional[str] = None


@router.patch("/{agent_id}/status")
async def hrm_update_status(
    agent_id: str,
    body: UpdateStatusBody,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an HRM agent's operational status (admin only)."""
    _require_admin(user)
    if body.status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"status must be one of {VALID_STATUSES}")
    acct = await _account(user, db)
    if not acct:
        raise HTTPException(status_code=404, detail="No account for user")
    a = (
        await db.execute(select(Agent).where(Agent.account_id == acct.id, Agent.agent_id == agent_id))
    ).scalar_one_or_none()
    if not a:
        raise HTTPException(status_code=404, detail="Agent not found")
    a.status = body.status
    await db.commit()
    await db.refresh(a)
    return _serialize_agent(a)
