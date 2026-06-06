"""Agency layer — /api/v1/agency/*.

Durable, runnable-agent surface: identity-state (rank, privileges, posture,
demotion), durable agent memory, and a persistent notification feed. State
changes are recorded to the PGL ledger so an agent's rank/posture history is
auditable. All workspace-scoped; honest empty states (no fabrication).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database.database import get_db
from backend.core.security.auth import get_current_user
from backend.db.models.agency import AgentState, AgentMemoryEntry, Notification
from backend.services.pgl_client import PGLClient

router = APIRouter(prefix="/agency", tags=["Agency"])

VALID_RANKS = ("recruit", "operator", "senior", "elite", "council")


def _ws(user) -> str:
    return user.workspace_id or "default"


async def _get_or_create_state(db: AsyncSession, ws: str, agent_id: str) -> AgentState:
    st = (await db.execute(
        select(AgentState).where(AgentState.workspace_id == ws, AgentState.agent_id == agent_id)
    )).scalar_one_or_none()
    if st is None:
        st = AgentState(workspace_id=ws, agent_id=agent_id)
        st.recompute()
        db.add(st)
        await db.flush()
    return st


def _state_dict(st: AgentState) -> dict:
    return {
        "agent_id": st.agent_id, "codename": st.codename, "rank": st.rank,
        "memory_tokens": st.memory_tokens, "privileges": st.privileges or [],
        "violations": st.violations, "clean_streak": st.clean_streak,
        "demotion_locked": st.demotion_locked, "posture_band": st.posture_band,
        "execution_eligible": st.execution_eligible,
        "updated_at": st.updated_at.isoformat() if st.updated_at else None,
    }


# --- Agent state / posture ---
@router.get("/agents/{agent_id}/state")
async def get_agent_state(agent_id: str, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    st = await _get_or_create_state(db, _ws(user), agent_id)
    await db.commit()
    return _state_dict(st)


@router.get("/agents")
async def list_agent_states(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    ws = _ws(user)
    rows = (await db.execute(
        select(AgentState).where(AgentState.workspace_id == ws).order_by(AgentState.agent_id.asc())
    )).scalars().all()
    if not rows:
        return {"items": [], "source": "empty", "reason": "No agent states yet. State is created when an agent is first inspected or governed."}
    return {"items": [_state_dict(s) for s in rows], "count": len(rows), "source": "db"}


class StateChange(BaseModel):
    rank: str | None = None
    grant_privilege: str | None = None
    revoke_privilege: str | None = None
    record_violation: bool = False
    record_clean_run: bool = False
    award_memory_tokens: int | None = Field(default=None, ge=0, le=100000)
    demotion_locked: bool | None = None
    codename: str | None = None


@router.post("/agents/{agent_id}/state")
async def update_agent_state(
    agent_id: str, body: StateChange,
    user=Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    """Adjust an agent's governed state. Recomputes posture and records a PGL
    ledger event so the rank/posture history is auditable."""
    role = (getattr(user, "role", "") or "").upper()
    if role not in ("OWNER", "ADMIN") and not getattr(user, "is_superuser", False):
        raise HTTPException(status_code=403, detail="Admin role required to change agent state")

    ws = _ws(user)
    st = await _get_or_create_state(db, ws, agent_id)
    before = _state_dict(st)

    if body.rank is not None:
        if body.rank not in VALID_RANKS:
            raise HTTPException(status_code=422, detail=f"rank must be one of {VALID_RANKS}")
        st.rank = body.rank
    if body.codename is not None:
        st.codename = body.codename[:128]
    if body.grant_privilege:
        privs = list(st.privileges or [])
        if body.grant_privilege not in privs:
            privs.append(body.grant_privilege)
        st.privileges = privs
    if body.revoke_privilege:
        st.privileges = [p for p in (st.privileges or []) if p != body.revoke_privilege]
    if body.record_violation:
        st.violations = (st.violations or 0) + 1
        st.clean_streak = 0
    if body.record_clean_run:
        st.clean_streak = (st.clean_streak or 0) + 1
    if body.award_memory_tokens is not None:
        st.memory_tokens = (st.memory_tokens or 0) + body.award_memory_tokens
    if body.demotion_locked is not None:
        st.demotion_locked = body.demotion_locked

    st.recompute()
    await db.flush()

    # Audit the state transition on the PGL ledger.
    pgl = PGLClient(db)
    ev = await pgl.record_event(ws, agent_id, None, "agent_state_change", {
        "before": {"rank": before["rank"], "posture": before["posture_band"], "violations": before["violations"]},
        "after": {"rank": st.rank, "posture": st.posture_band, "violations": st.violations},
    })

    # If the agent dropped to a restricted/suspended posture, raise a durable alarm.
    if st.posture_band in ("restricted", "suspended") and before["posture_band"] not in ("restricted", "suspended"):
        db.add(Notification(
            workspace_id=ws, kind="escalation", severity="critical",
            title=f"Agent {agent_id} posture dropped to {st.posture_band}",
            message=f"Violations={st.violations}, demotion_locked={st.demotion_locked}. Autonomous execution {'denied' if not st.execution_eligible else 'restricted'}.",
            source="agency", agent_id=agent_id, requires_action=True,
        ))

    await db.commit()
    return {"state": _state_dict(st), "pgl_event_hash": ev}


# --- Durable agent memory ---
class MemoryEntryIn(BaseModel):
    kind: str = Field(default="note")
    content: str = Field(..., min_length=1, max_length=8000)
    importance: float = Field(default=0.5, ge=0, le=1)
    tags: list[str] = Field(default_factory=list, max_length=16)


@router.get("/agents/{agent_id}/memory")
async def list_agent_memory(
    agent_id: str, limit: int = Query(100, ge=1, le=500),
    user=Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    ws = _ws(user)
    rows = (await db.execute(
        select(AgentMemoryEntry).where(
            AgentMemoryEntry.workspace_id == ws, AgentMemoryEntry.agent_id == agent_id
        ).order_by(desc(AgentMemoryEntry.importance), desc(AgentMemoryEntry.created_at)).limit(limit)
    )).scalars().all()
    if not rows:
        return {"items": [], "source": "empty", "reason": "No durable memory for this agent yet."}
    return {"items": [{
        "id": e.id, "kind": e.kind, "content": e.content, "importance": e.importance,
        "tags": e.tags or [], "created_at": e.created_at.isoformat() if e.created_at else None,
    } for e in rows], "count": len(rows), "source": "db"}


@router.post("/agents/{agent_id}/memory")
async def add_agent_memory(
    agent_id: str, body: MemoryEntryIn,
    user=Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    ws = _ws(user)
    entry = AgentMemoryEntry(
        workspace_id=ws, agent_id=agent_id, kind=body.kind,
        content=body.content, importance=body.importance, tags=body.tags,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return {"id": entry.id, "stored": True}


# --- Durable notifications (replaces the in-memory _alerts dict) ---
class NotificationIn(BaseModel):
    kind: str = Field(default="signal")
    severity: str = Field(default="info")
    title: str = Field(..., min_length=1, max_length=256)
    message: str = Field(default="", max_length=4000)
    source: str = Field(default="system")
    agent_id: str | None = None
    requires_action: bool = False


@router.get("/notifications")
async def list_notifications(
    unread_only: bool = Query(False), limit: int = Query(100, ge=1, le=500),
    user=Depends(get_current_user), db: AsyncSession = Depends(get_db),
):
    ws = _ws(user)
    q = select(Notification).where(Notification.workspace_id == ws)
    if unread_only:
        q = q.where(Notification.read.is_(False))
    rows = (await db.execute(q.order_by(desc(Notification.created_at)).limit(limit))).scalars().all()
    return {
        "items": [{
            "id": n.id, "kind": n.kind, "severity": n.severity, "title": n.title,
            "message": n.message, "source": n.source, "agent_id": n.agent_id,
            "requires_action": n.requires_action, "read": n.read, "resolved": n.resolved,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        } for n in rows],
        "count": len(rows), "source": "db",
    }


@router.post("/notifications")
async def create_notification(body: NotificationIn, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    n = Notification(
        workspace_id=_ws(user), kind=body.kind, severity=body.severity, title=body.title,
        message=body.message, source=body.source, agent_id=body.agent_id, requires_action=body.requires_action,
    )
    db.add(n)
    await db.commit()
    await db.refresh(n)
    return {"id": n.id, "created": True}


@router.post("/notifications/{notification_id}/read")
async def mark_read(notification_id: str, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    n = (await db.execute(select(Notification).where(
        Notification.id == notification_id, Notification.workspace_id == _ws(user)
    ))).scalar_one_or_none()
    if not n:
        raise HTTPException(status_code=404, detail="Notification not found")
    n.read = True
    await db.commit()
    return {"id": notification_id, "read": True}


@router.post("/notifications/{notification_id}/resolve")
async def resolve_notification(notification_id: str, user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    n = (await db.execute(select(Notification).where(
        Notification.id == notification_id, Notification.workspace_id == _ws(user)
    ))).scalar_one_or_none()
    if not n:
        raise HTTPException(status_code=404, detail="Notification not found")
    n.resolved = True
    n.read = True
    await db.commit()
    return {"id": notification_id, "resolved": True}


# --- Pulse overview (heartbeat-style truth: what's running, what needs you) ---
@router.get("/overview")
async def agency_overview(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    ws = _ws(user)
    posture_rows = (await db.execute(
        select(AgentState.posture_band, func.count()).where(AgentState.workspace_id == ws)
        .group_by(AgentState.posture_band)
    )).all()
    by_posture = {band: int(c) for band, c in posture_rows}
    unread = (await db.scalar(
        select(func.count()).select_from(Notification).where(
            Notification.workspace_id == ws, Notification.read.is_(False)
        )
    )) or 0
    needs_action = (await db.scalar(
        select(func.count()).select_from(Notification).where(
            Notification.workspace_id == ws, Notification.requires_action.is_(True), Notification.resolved.is_(False)
        )
    )) or 0
    total_agents = sum(by_posture.values())
    return {
        "total_agents": total_agents,
        "by_posture": by_posture,
        "suspended": by_posture.get("suspended", 0),
        "unread_notifications": int(unread),
        "needs_action": int(needs_action),
        "source": "db",
    }
