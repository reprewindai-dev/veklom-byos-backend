"""Agent Workforce routes — /api/v1/agents/*.

Implements the 12 endpoints required by docs/WIRING_MATRIX.md.

Data layer:
    - registry / fleet:    backend.db.models.agent.Agent
    - evidence:            backend.db.models.ledger.LedgerEvent
    - decisions / signals: backend.db.models.ai.ExecLog
                           and (where present) audit_logs

This router NEVER fabricates agents, runs, decisions, violations, signals,
evidence, or guardrails.  When no rows exist for the workspace's account,
each endpoint returns an empty list with an explicit `source` marker so the
UI can render a real empty state instead of fake data.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database.database import get_db
from backend.core.security.auth import get_current_user
from backend.db.models.agent import Account, Agent, AgentUser
from backend.db.models.ledger import LedgerEvent

router = APIRouter(prefix="/agents", tags=["Agent Workforce"])


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def _account_for_user(user, db: AsyncSession) -> Optional[Account]:
    """Resolve the Account row for the authenticated caller.

    The `accounts`/`agent_users` schema is a UACP V3 institutional ownership
    layer and is keyed by email, not workspace_id.  We look up by user email.
    """
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


def _serialize_agent(a: Agent) -> dict:
    return {
        "id": a.id,
        "agent_number": a.agent_number if a.agent_number is not None else a.id,
        "agent_id": a.agent_id,
        "codename": a.name,
        "name": a.name,
        "creator": a.creator,
        "group": a.declared_purpose,
        "jurisdiction": a.jurisdiction,
        "status": a.status,
        "tier": a.tier,
        "hrm_role": a.hrm_role,
        "account_id": a.account_id,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


def _serialize_ledger_event(e: LedgerEvent) -> dict:
    return {
        "id": e.id,
        "agent_id": e.agent_id,
        "event_id": e.event_id,
        "event_type": e.event_type,
        "actor": e.actor,
        "summary": e.summary,
        "details": e.details,
        "prev_event_hash": e.prev_event_hash,
        "event_hash": e.event_hash,
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }


def _empty(reason: str) -> dict:
    """Standard empty-state payload.  Carries an explicit reason so the UI
    can show the user why a section is empty rather than guessing."""
    return {
        "items": [],
        "source": "empty",
        "reason": reason,
    }


# ---------------------------------------------------------------------------
# Registry & fleet
# ---------------------------------------------------------------------------

@router.get("/registry")
async def registry(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    acct = await _account_for_user(user, db)
    if not acct:
        return _empty("No account row is associated with this user. Register the workspace via /api/v1/internal/uacp/* before listing agents.")
    rows = (await db.execute(
        select(Agent).where(Agent.account_id == acct.id).order_by(Agent.id.asc())
    )).scalars().all()
    return {
        "items": [_serialize_agent(a) for a in rows],
        "source": "db",
        "account_id": acct.id,
        "count": len(rows),
    }


@router.get("/registry/{agent_number}")
async def registry_detail(
    agent_number: int,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    acct = await _account_for_user(user, db)
    if not acct:
        raise HTTPException(status_code=404, detail="No account for user")
    a = (await db.execute(
        select(Agent).where(Agent.id == agent_number, Agent.account_id == acct.id)
    )).scalar_one_or_none()
    if not a:
        raise HTTPException(status_code=404, detail="Agent not found")
    return _serialize_agent(a)


@router.get("/fleet")
async def fleet(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Aggregate fleet view: status counts and recent activity per group."""
    acct = await _account_for_user(user, db)
    if not acct:
        return _empty("No account row for this user.")
    rows = (await db.execute(
        select(Agent.status, func.count(Agent.id))
        .where(Agent.account_id == acct.id)
        .group_by(Agent.status)
    )).all()
    by_status = {status: int(count) for status, count in rows}
    by_group = (await db.execute(
        select(Agent.declared_purpose, func.count(Agent.id))
        .where(Agent.account_id == acct.id)
        .group_by(Agent.declared_purpose)
    )).all()
    return {
        "as_of": _utcnow().isoformat(),
        "account_id": acct.id,
        "total": int(sum(by_status.values())),
        "by_status": by_status,
        "by_group": {group: int(count) for group, count in by_group},
        "source": "db",
    }


# ---------------------------------------------------------------------------
# Runs
# ---------------------------------------------------------------------------

class StartRunBody(BaseModel):
    agent_id: str
    summary: str
    details: dict = {}


@router.get("/runs")
async def list_runs(
    limit: int = Query(50, ge=1, le=500),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Runs are stored as ledger events of type `agent.run.started` and
    `agent.run.completed`.  We surface both so the UI can pair them.
    """
    acct = await _account_for_user(user, db)
    if not acct:
        return _empty("No account for this user.")
    rows = (await db.execute(
        select(LedgerEvent)
        .join(Agent, LedgerEvent.agent_id == Agent.id)
        .where(
            Agent.account_id == acct.id,
            LedgerEvent.event_type.in_(("agent.run.started", "agent.run.completed")),
        )
        .order_by(LedgerEvent.created_at.desc())
        .limit(limit)
    )).scalars().all()
    return {
        "items": [_serialize_ledger_event(e) for e in rows],
        "source": "ledger_events",
        "count": len(rows),
    }


@router.post("/runs")
async def start_run(
    body: StartRunBody,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Start a new agent run.  Admin-only by role to prevent unsafe trigger.

    Records a hash-chained `agent.run.started` event.  The actual workload
    dispatch is delegated to the operator/uacp-autonomous machinery — this
    endpoint only records the run intent in the agent ledger.
    """
    role = (getattr(user, "role", "") or "").upper()
    if role not in ("OWNER", "ADMIN") and not getattr(user, "is_superuser", False):
        raise HTTPException(status_code=403, detail="Admin role required")

    acct = await _account_for_user(user, db)
    if not acct:
        raise HTTPException(status_code=400, detail="No account row for user")

    a = (await db.execute(
        select(Agent).where(
            Agent.agent_id == body.agent_id, Agent.account_id == acct.id
        )
    )).scalar_one_or_none()
    if not a:
        raise HTTPException(status_code=404, detail="Agent not found")

    last = (await db.execute(
        select(LedgerEvent)
        .where(LedgerEvent.agent_id == a.id)
        .order_by(LedgerEvent.created_at.desc())
        .limit(1)
    )).scalar_one_or_none()
    prev = last.event_hash if last else None

    import uuid
    event_id = str(uuid.uuid4())
    payload = {
        "agent_id": a.agent_id,
        "summary": body.summary,
        "details": body.details,
        "prev": prev,
    }
    body_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    h = hashlib.sha256(body_bytes).hexdigest()

    ev = LedgerEvent(
        agent_id=a.id,
        event_id=event_id,
        event_type="agent.run.started",
        actor=user.email,
        summary=body.summary[:512],
        details=body.details,
        prev_event_hash=prev,
        event_hash=h,
    )
    db.add(ev)
    await db.commit()
    await db.refresh(ev)
    return _serialize_ledger_event(ev)


@router.patch("/runs/{run_id}/complete")
async def complete_run(
    run_id: str,
    body: dict,
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    role = (getattr(user, "role", "") or "").upper()
    if role not in ("OWNER", "ADMIN") and not getattr(user, "is_superuser", False):
        raise HTTPException(status_code=403, detail="Admin role required")

    acct = await _account_for_user(user, db)
    if not acct:
        raise HTTPException(status_code=400, detail="No account row for user")

    started = (await db.execute(
        select(LedgerEvent).where(LedgerEvent.event_id == run_id)
    )).scalar_one_or_none()
    if not started or started.event_type != "agent.run.started":
        raise HTTPException(status_code=404, detail="Run not found")
    a = (await db.execute(select(Agent).where(Agent.id == started.agent_id))).scalar_one_or_none()
    if not a or a.account_id != acct.id:
        raise HTTPException(status_code=404, detail="Run not found in account")

    last = (await db.execute(
        select(LedgerEvent)
        .where(LedgerEvent.agent_id == a.id)
        .order_by(LedgerEvent.created_at.desc())
        .limit(1)
    )).scalar_one_or_none()
    prev = last.event_hash if last else None

    import uuid
    event_id = str(uuid.uuid4())
    payload = {
        "run_id": run_id,
        "outcome": body.get("outcome", "ok"),
        "details": body.get("details", {}),
        "prev": prev,
    }
    body_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    h = hashlib.sha256(body_bytes).hexdigest()
    ev = LedgerEvent(
        agent_id=a.id,
        event_id=event_id,
        event_type="agent.run.completed",
        actor=user.email,
        summary=f"Run {run_id} complete: {payload['outcome']}",
        details=payload["details"],
        prev_event_hash=prev,
        event_hash=h,
    )
    db.add(ev)
    await db.commit()
    await db.refresh(ev)
    return _serialize_ledger_event(ev)


# ---------------------------------------------------------------------------
# Decision frames / signals / violations
# ---------------------------------------------------------------------------

@router.get("/decision-frames")
async def decision_frames(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    acct = await _account_for_user(user, db)
    if not acct:
        return _empty("No account for this user.")
    rows = (await db.execute(
        select(LedgerEvent)
        .join(Agent, LedgerEvent.agent_id == Agent.id)
        .where(
            Agent.account_id == acct.id,
            LedgerEvent.event_type == "agent.decision",
        )
        .order_by(LedgerEvent.created_at.desc())
        .limit(200)
    )).scalars().all()
    return {
        "items": [_serialize_ledger_event(e) for e in rows],
        "source": "ledger_events",
        "count": len(rows),
    }


@router.get("/signals")
async def signals(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    acct = await _account_for_user(user, db)
    if not acct:
        return _empty("No account for this user.")
    rows = (await db.execute(
        select(LedgerEvent)
        .join(Agent, LedgerEvent.agent_id == Agent.id)
        .where(
            Agent.account_id == acct.id,
            LedgerEvent.event_type == "agent.signal",
        )
        .order_by(LedgerEvent.created_at.desc())
        .limit(200)
    )).scalars().all()
    return {
        "items": [_serialize_ledger_event(e) for e in rows],
        "source": "ledger_events",
        "count": len(rows),
    }


@router.get("/violations")
async def violations(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    acct = await _account_for_user(user, db)
    if not acct:
        return _empty("No account for this user.")
    rows = (await db.execute(
        select(LedgerEvent)
        .join(Agent, LedgerEvent.agent_id == Agent.id)
        .where(
            Agent.account_id == acct.id,
            LedgerEvent.event_type.in_((
                "agent.violation",
                "agent.policy.blocked",
                "regulatory_breach",
            )),
        )
        .order_by(LedgerEvent.created_at.desc())
        .limit(200)
    )).scalars().all()
    return {
        "items": [_serialize_ledger_event(e) for e in rows],
        "source": "ledger_events",
        "count": len(rows),
    }


# ---------------------------------------------------------------------------
# Evidence
# ---------------------------------------------------------------------------

@router.get("/evidence")
async def evidence(
    limit: int = Query(100, ge=1, le=500),
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Surface every hash-chained ledger event for the account's agents.

    The hash chain is the evidence: each row carries event_hash + prev hash
    so any auditor can replay the chain and verify integrity.
    """
    acct = await _account_for_user(user, db)
    if not acct:
        return _empty("No account for this user.")
    rows = (await db.execute(
        select(LedgerEvent)
        .join(Agent, LedgerEvent.agent_id == Agent.id)
        .where(Agent.account_id == acct.id)
        .order_by(LedgerEvent.created_at.desc())
        .limit(limit)
    )).scalars().all()
    return {
        "items": [_serialize_ledger_event(e) for e in rows],
        "source": "ledger_events",
        "count": len(rows),
    }


@router.get("/monthly-report")
async def monthly_report(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    acct = await _account_for_user(user, db)
    if not acct:
        return _empty("No account for this user.")
    cutoff = _utcnow() - timedelta(days=30)
    total = (await db.execute(
        select(func.count(LedgerEvent.id))
        .join(Agent, LedgerEvent.agent_id == Agent.id)
        .where(Agent.account_id == acct.id, LedgerEvent.created_at >= cutoff)
    )).scalar() or 0
    by_type_rows = (await db.execute(
        select(LedgerEvent.event_type, func.count(LedgerEvent.id))
        .join(Agent, LedgerEvent.agent_id == Agent.id)
        .where(Agent.account_id == acct.id, LedgerEvent.created_at >= cutoff)
        .group_by(LedgerEvent.event_type)
    )).all()
    return {
        "window_days": 30,
        "as_of": _utcnow().isoformat(),
        "account_id": acct.id,
        "events_total": int(total),
        "by_event_type": {t: int(c) for t, c in by_type_rows},
        "source": "ledger_events",
    }


# ---------------------------------------------------------------------------
# Guardrails
# ---------------------------------------------------------------------------

@router.get("/guardrails")
async def guardrails(
    user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Static guardrail manifest exposed to the workforce UI.

    These are the policy guardrails enforced by the GPC pipeline before any
    agent run.  They are version-pinned and not configurable from the UI.
    """
    return {
        "source": "static",
        "version": "1.0",
        "items": [
            {
                "id": "gr.pii_redaction",
                "name": "PII redaction at ingress",
                "description": "All inputs are scanned for PII via /api/v1/privacy/detect-pii before they reach a model.",
                "enforced_by": "gpc",
            },
            {
                "id": "gr.policy_gate",
                "name": "Policy-checked plan compilation",
                "description": "Every plan must pass GPC compile before execution.",
                "enforced_by": "gpc",
            },
            {
                "id": "gr.byok_isolation",
                "name": "BYOK isolation",
                "description": "Customer-tenant runs may only use customer-owned provider keys; founder/admin keys are never leaked to a customer tenant.",
                "enforced_by": "providers.routing",
            },
            {
                "id": "gr.kill_switch",
                "name": "Kill switch",
                "description": "Workspace owners can halt all agent runs at /api/v1/kill-switch/activate.",
                "enforced_by": "kill_switch",
            },
            {
                "id": "gr.audit_chain",
                "name": "Hash-chained audit ledger",
                "description": "Every audit event is appended to a SHA-256 chain verified at /api/v1/audit/verify/{log_id}.",
                "enforced_by": "audit",
            },
            {
                "id": "gr.regulatory_breach_veto",
                "name": "Regulatory-breach veto",
                "description": "Any chain-integrity break fires the regulatory_breach veto and quarantines the agent.",
                "enforced_by": "ledger_worker",
            },
        ],
    }
