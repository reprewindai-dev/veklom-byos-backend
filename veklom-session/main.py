"""
Veklom — FastAPI control plane.
Wraps AgentSession + EnforcerAgent as live HTTP endpoints.
Production-ready starting point.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
import uuid
import json
import time

from session import (
    AgentSession, AgentIdentity, PolicyScope,
    Transport, SessionStatus
)
from enforcer import (
    EnforcerAgent, Intervention,
    rule_cost_warning,
    rule_deny_on_repeated_failures,
    rule_block_denied_action_pattern,
    rule_hold_on_sensitive_jurisdiction,
)
import types

app = FastAPI(title="Veklom Control Plane", version="0.1.0")

# ── In-memory session store (replace with Redis/Postgres in prod) ───────────────
_sessions: dict[str, AgentSession] = {}
_enforcers: dict[str, EnforcerAgent] = {}
_audit_store: dict[str, dict] = {}   # session_id → signed audit record


# ── Enforcer wiring helper ─────────────────────────────────────────────────────
def _wire_enforcer(session: AgentSession, enforcer: EnforcerAgent):
    original_append = session._append.__func__
    def observed_append(self_inner, ttype, data):
        t = original_append(self_inner, ttype, data)
        enforcer.observe(t, self_inner)
        return t
    session._append = types.MethodType(observed_append, session)


# ── Request / response models ──────────────────────────────────────────────────
class OpenSessionRequest(BaseModel):
    agent_id:         str
    agent_name:       str
    model:            str
    transport:        str = "openai"
    credentials_ref:  str
    owner:            str
    policy_id:        str
    rules:            list[str] = []
    max_cost_usd:     float = 10.0
    require_approval: list[str] = []
    deny:             list[str] = []
    jurisdiction:     str = "GLOBAL"
    cost_warn_at:     float = 5.0


class IntentRequest(BaseModel):
    intent: str
    source: str = "user"


class ActionRequest(BaseModel):
    action_type: str
    action_data: dict = {}


class ApproveRequest(BaseModel):
    action_type: str
    approved_by: str


class ExecuteRequest(BaseModel):
    action_type: str
    result:      dict = {}


class CostRequest(BaseModel):
    amount_usd: float
    detail:     str = ""


class PolicyInjectRequest(BaseModel):
    new_rules:   list[str]
    injected_by: str = "policy_engine"


class KillRequest(BaseModel):
    reason: str = "manual kill switch"


# ── Session lifecycle ──────────────────────────────────────────────────────────
@app.post("/sessions", status_code=201)
def open_session(req: OpenSessionRequest):
    """Open a new governed agent session."""
    identity = AgentIdentity(
        agent_id    = req.agent_id,
        agent_name  = req.agent_name,
        version     = "1.0",
        transport   = Transport(req.transport),
        model       = req.model,
        credentials = req.credentials_ref,
        owner       = req.owner,
    )
    policy = PolicyScope(
        policy_id        = req.policy_id,
        rules            = req.rules,
        max_cost_usd     = req.max_cost_usd,
        require_approval = req.require_approval,
        deny             = req.deny,
        jurisdiction     = req.jurisdiction,
    )
    session = AgentSession(identity, policy)

    # Attach enforcer
    enforcer = EnforcerAgent(
        enforcer_id = f"enforcer-{session.session_id[:8]}",
        rules = [
            rule_cost_warning(req.cost_warn_at),
            rule_deny_on_repeated_failures(3),
            rule_block_denied_action_pattern("bypass_kyc", 2),
            rule_hold_on_sensitive_jurisdiction(["CN", "RU", "IR"]),
        ],
    )
    _wire_enforcer(session, enforcer)

    _sessions[session.session_id] = session
    _enforcers[session.session_id] = enforcer

    return {
        "session_id": session.session_id,
        "status":     session.status,
        "policy_id":  policy.policy_id,
    }


@app.get("/sessions/{session_id}")
def get_session(session_id: str):
    s = _sessions.get(session_id)
    if not s:
        raise HTTPException(404, "Session not found")
    return {
        "session_id":   s.session_id,
        "status":       s.status,
        "cost_usd":     s.cost_usd,
        "transitions":  len(s.transitions),
        "agent_id":     s.identity.agent_id,
        "model":        s.identity.model,
        "transport":    s.identity.transport,
        "policy_id":    s.policy.policy_id,
        "chain_intact": s.verify_chain(),
    }


@app.post("/sessions/{session_id}/intent")
def receive_intent(session_id: str, req: IntentRequest):
    s = _get_active(session_id)
    t = s.receive_intent(req.intent, req.source)
    return {"seq": t.seq, "type": t.type}


@app.post("/sessions/{session_id}/policy-check")
def policy_check(session_id: str, req: ActionRequest):
    s = _get_active(session_id)
    allowed = s.check_policy(req.action_type, req.action_data)
    return {
        "allowed":     allowed,
        "action_type": req.action_type,
        "status":      s.status,
    }


@app.post("/sessions/{session_id}/approve")
def approve_action(session_id: str, req: ApproveRequest):
    s = _get_active(session_id)
    t = s.approve_action(req.action_type, req.approved_by)
    return {"seq": t.seq, "approved_by": req.approved_by}


@app.post("/sessions/{session_id}/execute")
def execute_action(session_id: str, req: ExecuteRequest):
    s = _get_active(session_id)
    t = s.execute_action(req.action_type, req.result)
    return {"seq": t.seq, "type": t.type}


@app.post("/sessions/{session_id}/cost")
def record_cost(session_id: str, req: CostRequest):
    s = _get_active(session_id)
    t = s.record_cost(req.amount_usd, req.detail)
    return {"seq": t.seq, "total_usd": s.cost_usd, "status": s.status}


@app.post("/sessions/{session_id}/inject-policy")
def inject_policy(session_id: str, req: PolicyInjectRequest):
    s = _get_active(session_id)
    t = s.inject_policy(req.new_rules, req.injected_by)
    return {"seq": t.seq, "new_rules": req.new_rules}


@app.post("/sessions/{session_id}/kill")
def kill_session(session_id: str, req: KillRequest):
    s = _sessions.get(session_id)
    if not s:
        raise HTTPException(404, "Session not found")
    record = s.kill(req.reason)
    _audit_store[session_id] = json.loads(record.to_json())
    return {
        "session_id": session_id,
        "status":     "killed",
        "reason":     req.reason,
        "signature":  record.signature[:16] + "...",
    }


@app.post("/sessions/{session_id}/close")
def close_session(session_id: str, outcome: str = "success"):
    s = _get_active(session_id)
    record = s.close(outcome)
    _audit_store[session_id] = json.loads(record.to_json())
    return {
        "session_id":  session_id,
        "status":      record.status,
        "total_usd":   record.total_usd,
        "transitions": len(record.transitions),
        "chain_hash":  record.chain_hash[:16] + "...",
        "signature":   record.signature[:16] + "...",
        "valid":       record.verify("veklom-signing-key-prod"),
    }


# ── Audit endpoints ────────────────────────────────────────────────────────────
@app.get("/sessions/{session_id}/audit")
def get_audit(session_id: str):
    """Get full signed audit record for a closed session."""
    record = _audit_store.get(session_id)
    if not record:
        # Session still open — return live transitions
        s = _sessions.get(session_id)
        if not s:
            raise HTTPException(404, "Session not found")
        return {
            "session_id":  session_id,
            "status":      s.status,
            "transitions": [t.to_dict() for t in s.transitions],
            "chain_intact": s.verify_chain(),
            "signed":      False,
        }
    return record


@app.get("/sessions/{session_id}/enforcer")
def get_enforcer_log(session_id: str):
    """Get enforcer interventions for a session."""
    e = _enforcers.get(session_id)
    if not e:
        raise HTTPException(404, "Enforcer not found")
    from dataclasses import asdict
    return {
        "enforcer_id":    e.enforcer_id,
        "interventions":  [asdict(i) for i in e.interventions],
        "total":          len(e.interventions),
    }


# ── Kill switch — all sessions ─────────────────────────────────────────────────
@app.post("/kill-all")
def kill_all(reason: str = "global kill switch"):
    """Emergency: kill every active session."""
    killed = []
    for sid, s in _sessions.items():
        if s.status == SessionStatus.ACTIVE:
            record = s.kill(reason)
            _audit_store[sid] = json.loads(record.to_json())
            killed.append(sid)
    return {"killed": killed, "count": len(killed)}


# ── Helpers ────────────────────────────────────────────────────────────────────
def _get_active(session_id: str) -> AgentSession:
    s = _sessions.get(session_id)
    if not s:
        raise HTTPException(404, "Session not found")
    if s.status != SessionStatus.ACTIVE:
        raise HTTPException(409, f"Session is {s.status} — not active")
    return s
