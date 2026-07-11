"""
Veklom AgentSession — Core execution primitive.
Every agent run is a stateful session with ordered transitions,
live policy injection, and signed audit evidence.
"""

import uuid
import time
import hashlib
import hmac
import json
from enum import Enum
from typing import Any, Optional
from dataclasses import dataclass, field, asdict


# ── Transport types ────────────────────────────────────────────────────────────
class Transport(str, Enum):
    OPENAI     = "openai"
    ANTHROPIC  = "anthropic"
    BEDROCK    = "bedrock"
    GEMINI     = "gemini"
    OLLAMA     = "ollama"
    LOCAL      = "local"
    AZURE      = "azure_openai"


# ── Session status ─────────────────────────────────────────────────────────────
class SessionStatus(str, Enum):
    ACTIVE    = "active"
    PAUSED    = "paused"
    COMPLETED = "completed"
    ABORTED   = "aborted"
    KILLED    = "killed"


# ── Transition types ───────────────────────────────────────────────────────────
class TransitionType(str, Enum):
    SESSION_OPEN        = "session.open"
    POLICY_CHECK        = "policy.check"
    POLICY_INJECTED     = "policy.injected"
    INTENT_RECEIVED     = "intent.received"
    PLAN_COMPILED       = "plan.compiled"
    ACTION_REQUESTED    = "action.requested"
    ACTION_APPROVED     = "action.approved"
    ACTION_DENIED       = "action.denied"
    ACTION_EXECUTED     = "action.executed"
    COST_RECORDED       = "cost.recorded"
    ERROR_RECORDED      = "error.recorded"
    SESSION_PAUSED      = "session.paused"
    SESSION_RESUMED     = "session.resumed"
    SESSION_KILLED      = "session.killed"
    SESSION_CLOSED      = "session.closed"


# ── Single state transition ────────────────────────────────────────────────────
@dataclass
class Transition:
    seq:        int
    type:       TransitionType
    timestamp:  float
    data:       dict
    prev_hash:  str  # chains to previous transition — makes log tamper-evident

    def to_dict(self) -> dict:
        return asdict(self)

    def compute_hash(self) -> str:
        payload = json.dumps(self.to_dict(), sort_keys=True, default=str)
        return hashlib.sha256(payload.encode()).hexdigest()


# ── Agent identity ─────────────────────────────────────────────────────────────
@dataclass
class AgentIdentity:
    agent_id:    str
    agent_name:  str
    version:     str
    transport:   Transport
    model:       str           # e.g. "gpt-4o", "claude-3-5-sonnet", "llama3"
    credentials: str           # credential reference ID — never the actual secret
    owner:       str           # tenant / org ID


# ── Policy scope ───────────────────────────────────────────────────────────────
@dataclass
class PolicyScope:
    policy_id:       str
    rules:           list[str]     # active rule IDs
    max_cost_usd:    float         # per-session cost ceiling
    require_approval: list[str]    # action types that need human approval
    deny:            list[str]     # action types that are always blocked
    jurisdiction:    str           # e.g. "EU", "US", "GLOBAL"


# ── The session ────────────────────────────────────────────────────────────────
class AgentSession:
    """
    The core Veklom primitive.
    One session per agent run. Portable across transports.
    Every event is a chained, ordered state transition.
    Produces signed audit evidence on close.
    """

    def __init__(
        self,
        identity: AgentIdentity,
        policy:   PolicyScope,
        signing_key: Optional[str] = None,
    ):
        self.session_id   = str(uuid.uuid4())
        self.identity     = identity
        self.policy       = policy
        self.status       = SessionStatus.ACTIVE
        self.transitions: list[Transition] = []
        self.cost_usd     = 0.0
        self._signing_key = signing_key or "dev-key-replace-in-prod"
        self._seq         = 0

        self._append(TransitionType.SESSION_OPEN, {
            "agent_id":   identity.agent_id,
            "transport":  identity.transport,
            "model":      identity.model,
            "policy_id":  policy.policy_id,
            "rules":      policy.rules,
        })

    # ── Internal ──────────────────────────────────────────────────────────────

    def _prev_hash(self) -> str:
        if not self.transitions:
            return "genesis"
        return self.transitions[-1].compute_hash()

    def _append(self, type: TransitionType, data: dict) -> Transition:
        t = Transition(
            seq       = self._seq,
            type      = type,
            timestamp = time.time(),
            data      = data,
            prev_hash = self._prev_hash(),
        )
        self.transitions.append(t)
        self._seq += 1
        return t

    def _guard(self):
        if self.status not in (SessionStatus.ACTIVE,):
            raise RuntimeError(f"Session {self.session_id} is {self.status} — cannot accept new transitions.")

    # ── Public API ────────────────────────────────────────────────────────────

    def receive_intent(self, intent: str, source: str = "user") -> Transition:
        """Record incoming agent intent."""
        self._guard()
        return self._append(TransitionType.INTENT_RECEIVED, {
            "intent": intent,
            "source": source,
        })

    def compile_plan(self, plan: dict) -> Transition:
        """Record the compiled execution plan."""
        self._guard()
        return self._append(TransitionType.PLAN_COMPILED, {"plan": plan})

    def check_policy(self, action_type: str, action_data: dict) -> bool:
        """
        Enforce policy against a proposed action.
        Records the check and returns True (approved) or False (denied).
        """
        self._guard()

        denied  = action_type in self.policy.deny
        blocked = self.cost_usd >= self.policy.max_cost_usd

        if denied or blocked:
            reason = "action type denied by policy" if denied else "cost ceiling reached"
            self._append(TransitionType.ACTION_DENIED, {
                "action_type": action_type,
                "action_data": action_data,
                "reason":      reason,
            })
            return False

        needs_approval = action_type in self.policy.require_approval
        self._append(TransitionType.POLICY_CHECK, {
            "action_type":     action_type,
            "action_data":     action_data,
            "needs_approval":  needs_approval,
            "result":          "pending_approval" if needs_approval else "approved",
        })
        return not needs_approval  # caller must handle approval flow

    def approve_action(self, action_type: str, approved_by: str) -> Transition:
        """Record human approval for a held action."""
        self._guard()
        return self._append(TransitionType.ACTION_APPROVED, {
            "action_type": action_type,
            "approved_by": approved_by,
        })

    def execute_action(self, action_type: str, result: Any) -> Transition:
        """Record successful execution of an action."""
        self._guard()
        return self._append(TransitionType.ACTION_EXECUTED, {
            "action_type": action_type,
            "result":      result,
        })

    def record_cost(self, usd: float, detail: str = "") -> Transition:
        """Accumulate cost and record it. Abort if ceiling breached."""
        self._guard()
        self.cost_usd += usd
        t = self._append(TransitionType.COST_RECORDED, {
            "increment_usd": usd,
            "total_usd":     self.cost_usd,
            "detail":        detail,
        })
        if self.cost_usd >= self.policy.max_cost_usd:
            self.kill(reason="cost ceiling exceeded automatically")
        return t

    def inject_policy(self, new_rules: list[str], injected_by: str = "policy_engine") -> Transition:
        """
        Live policy injection — push new rules into a running session
        without stopping it. This is the actor-model policy message in practice.
        """
        self._guard()
        old_rules = list(self.policy.rules)
        self.policy.rules = new_rules
        return self._append(TransitionType.POLICY_INJECTED, {
            "old_rules":    old_rules,
            "new_rules":    new_rules,
            "injected_by":  injected_by,
        })

    def record_error(self, error: str, fatal: bool = False) -> Transition:
        self._guard()
        t = self._append(TransitionType.ERROR_RECORDED, {
            "error": error,
            "fatal": fatal,
        })
        if fatal:
            self.abort(reason=error)
        return t

    def pause(self, reason: str = "") -> Transition:
        self._guard()
        self.status = SessionStatus.PAUSED
        return self._append(TransitionType.SESSION_PAUSED, {"reason": reason})

    def resume(self) -> Transition:
        if self.status != SessionStatus.PAUSED:
            raise RuntimeError("Session is not paused.")
        self.status = SessionStatus.ACTIVE
        return self._append(TransitionType.SESSION_RESUMED, {})

    def kill(self, reason: str = "kill switch activated") -> "SignedAuditRecord":
        """Hard stop — immediate, regardless of current state."""
        self.status = SessionStatus.KILLED
        self._append(TransitionType.SESSION_KILLED, {"reason": reason})
        return self._sign_and_close()

    def abort(self, reason: str = "") -> "SignedAuditRecord":
        self.status = SessionStatus.ABORTED
        self._append(TransitionType.SESSION_CLOSED, {"reason": reason, "outcome": "aborted"})
        return self._sign_and_close()

    def close(self, outcome: str = "success") -> "SignedAuditRecord":
        """Normal close — produces signed audit evidence."""
        if self.status == SessionStatus.ACTIVE:
            self.status = SessionStatus.COMPLETED
        self._append(TransitionType.SESSION_CLOSED, {
            "outcome":   outcome,
            "total_usd": self.cost_usd,
        })
        return self._sign_and_close()

    # ── Signing ───────────────────────────────────────────────────────────────

    def _sign_and_close(self) -> "SignedAuditRecord":
        chain_hash = self.transitions[-1].compute_hash()
        payload = json.dumps({
            "session_id":  self.session_id,
            "agent_id":    self.identity.agent_id,
            "model":       self.identity.model,
            "transport":   self.identity.transport,
            "policy_id":   self.policy.policy_id,
            "status":      self.status,
            "total_usd":   self.cost_usd,
            "transitions": len(self.transitions),
            "chain_hash":  chain_hash,
        }, sort_keys=True)

        signature = hmac.new(
            self._signing_key.encode(),
            payload.encode(),
            hashlib.sha256,
        ).hexdigest()

        return SignedAuditRecord(
            session_id   = self.session_id,
            agent_id     = self.identity.agent_id,
            model        = self.identity.model,
            transport    = self.identity.transport,
            policy_id    = self.policy.policy_id,
            status       = self.status,
            total_usd    = self.cost_usd,
            transitions  = [t.to_dict() for t in self.transitions],
            chain_hash   = chain_hash,
            signature    = signature,
        )

    # ── Replay ────────────────────────────────────────────────────────────────

    def verify_chain(self) -> bool:
        """Verify the transition chain has not been tampered with."""
        for i, t in enumerate(self.transitions):
            expected_prev = "genesis" if i == 0 else self.transitions[i-1].compute_hash()
            if t.prev_hash != expected_prev:
                return False
        return True


# ── Signed audit record ────────────────────────────────────────────────────────
@dataclass
class SignedAuditRecord:
    session_id:  str
    agent_id:    str
    model:       str
    transport:   str
    policy_id:   str
    status:      SessionStatus
    total_usd:   float
    transitions: list[dict]
    chain_hash:  str
    signature:   str

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, default=str)

    def verify(self, signing_key: str) -> bool:
        payload = json.dumps({
            "session_id":  self.session_id,
            "agent_id":    self.agent_id,
            "model":       self.model,
            "transport":   self.transport,
            "policy_id":   self.policy_id,
            "status":      self.status,
            "total_usd":   self.total_usd,
            "transitions": len(self.transitions),
            "chain_hash":  self.chain_hash,
        }, sort_keys=True)
        expected = hmac.new(
            signing_key.encode(),
            payload.encode(),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(self.signature, expected)
