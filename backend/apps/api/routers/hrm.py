"""HRM (Human-Resource Management) Agent sub-router — /api/v1/agents/hrm/*.

Provides HRM-specific views over the agents table: performance auditing,
single-agent status, monitor listing, Zeno interrogation, and telemetry
report synthesis.

Anti-fakery contract:
  - All data comes from the `agents` table or `ledger_events` table.
  - When no rows match, an explicit empty-state payload is returned.
  - Zeno interrogation is a gated write — it records intent in the ledger
    but performs no simulated analysis.
  - Telemetry synthesis reads real ledger events for the requested agents.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database.database import get_db
from backend.core.security.auth import get_current_user
from backend.db.models.agent import Account, Agent, AgentUser
from backend.db.models.ledger import LedgerEvent

router = APIRouter(prefix="/agents/hrm", tags=["HRM Agents"])


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def _account_for_user(user, db: AsyncSession) -> Optional[Account]:
    if not getattr(user, "email", None):
        return None
    au = (
        await db.execute(
            select(AgentUser).where(AgentUser.email == user.email).limit(1)
        )
    ).scalar_one_or_none()
    if not au:
        return None
    return (
        await db.execute(select(Account).where(Account.id == au.account_id))
    ).scalar_one_or_none()


def _empty(reason: str) -> dict:
    return {"items": [], "source": "empty", "reason": reason}


def _serialize_agent(a: Agent) -> dict:
    return {
        "id": a.id,
        "agent_number": a.agent_number if a.agent_number is not None else a.id,
        "agent_id": a.agent_id,
        "name": a.name,
        "creator": a.creator,
        "jurisdiction": a.jurisdiction,
        "declared_purpose": a.declared_purpose,
        "status": a.status,
        "tier": a.tier,
        "hrm_role": a.hrm_role,
        "account_id": a.account_id,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


def _serialize_event(e: LedgerEvent) -> dict:
    return {
        "id": e.id,
        "event_id": e.event_id,
        "agent_id": e.agent_id,
        "event_type": e.event_type,
        "actor": e.actor,
        "summary": e.summary,
        "details": e.details,
        "prev_event_hash": e.prev_event_hash,
        "event_hash": e.event_hash,
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }


# ---------------------------------------------------------------------------
# GET /api/v1/agents/hrm/performance
# Audit HRM agent performance across all registered HRM-tier agents.
# ---------------------------------------------------------------------------

@router.get("/performance")
async def hrm_performance(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Aggregate performance metrics for every agent with tier='HRM'.

    Metrics are derived from ledger events:
      - runs_started: count of agent.run.started events in the last 30 days
      - runs_completed: count of agent.run.completed
      - violations: count of agent.violation / agent.policy.blocked events
      - signals: count of agent.signal events
    """
    acct = await _account_for_user(user, db)
    if not acct:
        return _empty("No account row for this user. Register via /api/v1/internal/uacp/* first.")

    hrm_agents = (await db.execute(
        select(Agent)
        .where(Agent.account_id == acct.id, Agent.tier == "HRM")
        .order_by(Agent.agent_number.asc().nullslast(), Agent.id.asc())
    )).scalars().all()

    if not hrm_agents:
        return _empty("No agents with tier='HRM' are registered for this account.")

    cutoff = _utcnow() - timedelta(days=30)
    agent_ids = [a.id for a in hrm_agents]

    def _count_q(event_types):
        return (
            select(LedgerEvent.agent_id, func.count(LedgerEvent.id))
            .where(
                LedgerEvent.agent_id.in_(agent_ids),
                LedgerEvent.event_type.in_(event_types),
                LedgerEvent.created_at >= cutoff,
            )
            .group_by(LedgerEvent.agent_id)
        )

    runs_started = {aid: int(c) for aid, c in (await db.execute(_count_q(["agent.run.started"]))).all()}
    runs_completed = {aid: int(c) for aid, c in (await db.execute(_count_q(["agent.run.completed"]))).all()}
    violations = {aid: int(c) for aid, c in (await db.execute(_count_q(["agent.violation", "agent.policy.blocked"]))).all()}
    signals = {aid: int(c) for aid, c in (await db.execute(_count_q(["agent.signal"]))).all()}

    items = []
    for a in hrm_agents:
        items.append({
            **_serialize_agent(a),
            "metrics_window_days": 30,
            "runs_started": runs_started.get(a.id, 0),
            "runs_completed": runs_completed.get(a.id, 0),
            "violations": violations.get(a.id, 0),
            "signals": signals.get(a.id, 0),
        })

    return {
        "as_of": _utcnow().isoformat(),
        "account_id": acct.id,
        "hrm_agent_count": len(items),
        "items": items,
        "source": "db+ledger",
    }


# ---------------------------------------------------------------------------
# GET /api/v1/agents/hrm/monitors
# Identify all active HRM Monitor agents.
# MUST come before /{agent_number} to avoid route shadowing.
# ---------------------------------------------------------------------------

@router.get("/monitors")
async def hrm_monitors(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all agents with hrm_role='HRM-Monitor' and status='active'."""
    acct = await _account_for_user(user, db)
    if not acct:
        return _empty("No account row for this user.")

    rows = (await db.execute(
        select(Agent)
        .where(
            Agent.account_id == acct.id,
            Agent.hrm_role == "HRM-Monitor",
            Agent.status == "active",
        )
        .order_by(Agent.agent_number.asc().nullslast(), Agent.id.asc())
    )).scalars().all()

    return {
        "as_of": _utcnow().isoformat(),
        "account_id": acct.id,
        "items": [_serialize_agent(a) for a in rows],
        "count": len(rows),
        "source": "db",
    }


# ---------------------------------------------------------------------------
# GET /api/v1/agents/hrm/telemetry-report
# Synthesize a telemetry report for specified HRM-Sync agents.
# MUST come before /{agent_number} to avoid route shadowing.
# ---------------------------------------------------------------------------

@router.get("/telemetry-report")
async def hrm_telemetry_report(
    agent_numbers: str = Query(
        ...,
        description="Comma-separated agent_number values, e.g. '15,30,45'",
        alias="agents",
    ),
    window_days: int = Query(7, ge=1, le=90),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Synthesize a telemetry report for named HRM-Sync agents.

    Reads the ledger for the requested agent_numbers and returns event
    counts, last-seen timestamps, and hash-chain tail for each.
    No data is fabricated — if an agent has zero events the entry reports
    zeros with source='ledger_empty'.
    """
    acct = await _account_for_user(user, db)
    if not acct:
        return _empty("No account row for this user.")

    try:
        nums = [int(x.strip()) for x in agent_numbers.split(",") if x.strip()]
    except ValueError:
        raise HTTPException(status_code=422, detail="agents must be comma-separated integers")

    if not nums:
        raise HTTPException(status_code=422, detail="At least one agent number required")

    agents_by_num = (await db.execute(
        select(Agent).where(
            Agent.account_id == acct.id,
            Agent.agent_number.in_(nums),
        )
    )).scalars().all()
    found_nums = {a.agent_number for a in agents_by_num}
    missing_nums = [n for n in nums if n not in found_nums]

    cutoff = _utcnow() - timedelta(days=window_days)
    report = []

    for a in agents_by_num:
        events = (await db.execute(
            select(LedgerEvent)
            .where(LedgerEvent.agent_id == a.id, LedgerEvent.created_at >= cutoff)
            .order_by(LedgerEvent.created_at.desc())
            .limit(500)
        )).scalars().all()

        last_event = events[0] if events else None
        by_type = {}
        for e in events:
            by_type[e.event_type] = by_type.get(e.event_type, 0) + 1

        report.append({
            "agent_number": a.agent_number,
            "agent_id": a.agent_id,
            "name": a.name,
            "tier": a.tier,
            "hrm_role": a.hrm_role,
            "status": a.status,
            "window_days": window_days,
            "event_count": len(events),
            "by_event_type": by_type,
            "last_event_at": last_event.created_at.isoformat() if last_event else None,
            "chain_tail": last_event.event_hash if last_event else None,
            "source": "ledger" if events else "ledger_empty",
        })

    return {
        "as_of": _utcnow().isoformat(),
        "requested_agent_numbers": nums,
        "found": [a.agent_number for a in agents_by_num],
        "not_found": missing_nums,
        "window_days": window_days,
        "report": report,
        "source": "db+ledger",
    }


# ---------------------------------------------------------------------------
# GET /api/v1/agents/hrm/{agent_number}
# Status of a specific HRM agent.
# ---------------------------------------------------------------------------

@router.get("/{agent_number}")
async def hrm_agent_detail(
    agent_number: int,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve full details for the HRM agent with the given agent_number."""
    acct = await _account_for_user(user, db)
    if not acct:
        raise HTTPException(status_code=404, detail="No account row for this user")

    a = (await db.execute(
        select(Agent).where(
            Agent.account_id == acct.id,
            Agent.agent_number == agent_number,
        )
    )).scalar_one_or_none()
    if not a:
        raise HTTPException(status_code=404, detail=f"Agent {agent_number} not found")

    last_event = (await db.execute(
        select(LedgerEvent)
        .where(LedgerEvent.agent_id == a.id)
        .order_by(LedgerEvent.created_at.desc())
        .limit(1)
    )).scalar_one_or_none()

    return {
        **_serialize_agent(a),
        "last_ledger_event": _serialize_event(last_event) if last_event else None,
        "source": "db",
    }


# ---------------------------------------------------------------------------
# POST /api/v1/agents/hrm/{agent_number}/zeno-interrogation
# Run Zeno interrogation on an HRM Monitor's memory vault.
# ---------------------------------------------------------------------------

class ZenoInterrogationBody(BaseModel):
    scope: str = "memory_vault"
    note: Optional[str] = None


@router.post("/{agent_number}/zeno-interrogation")
async def hrm_zeno_interrogation(
    agent_number: int,
    body: ZenoInterrogationBody,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Initiate a Zeno interrogation for the specified agent.

    Records the interrogation intent as a hash-chained ledger event of type
    `hrm.zeno.interrogation.initiated`.  Actual interrogation analysis is
    performed by the autonomous worker when it processes the event — this
    endpoint only registers the intent.

    Requires OWNER or ADMIN role.
    """
    role = (getattr(user, "role", "") or "").upper()
    if role not in ("OWNER", "ADMIN") and not getattr(user, "is_superuser", False):
        raise HTTPException(status_code=403, detail="Admin role required for Zeno interrogation")

    acct = await _account_for_user(user, db)
    if not acct:
        raise HTTPException(status_code=400, detail="No account row for user")

    a = (await db.execute(
        select(Agent).where(
            Agent.account_id == acct.id,
            Agent.agent_number == agent_number,
        )
    )).scalar_one_or_none()
    if not a:
        raise HTTPException(status_code=404, detail=f"Agent {agent_number} not found")

    last = (await db.execute(
        select(LedgerEvent)
        .where(LedgerEvent.agent_id == a.id)
        .order_by(LedgerEvent.created_at.desc())
        .limit(1)
    )).scalar_one_or_none()
    prev = last.event_hash if last else None

    event_id = str(uuid.uuid4())
    payload = {
        "agent_id": a.agent_id,
        "scope": body.scope,
        "note": body.note,
        "initiated_by": user.email,
        "prev": prev,
    }
    body_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    h = hashlib.sha256(body_bytes).hexdigest()

    ev = LedgerEvent(
        agent_id=a.id,
        event_id=event_id,
        event_type="hrm.zeno.interrogation.initiated",
        actor=user.email,
        summary=f"Zeno interrogation initiated on agent {agent_number} (scope={body.scope})",
        details={"scope": body.scope, "note": body.note},
        prev_event_hash=prev,
        event_hash=h,
    )
    db.add(ev)
    await db.commit()
    await db.refresh(ev)

    return {
        "status": "initiated",
        "agent_number": agent_number,
        "agent_id": a.agent_id,
        "event": _serialize_event(ev),
        "note": "Interrogation intent recorded in ledger. Autonomous worker will process when scheduled.",
    }
