"""
Veklom EnforcerAgent — passive session watcher.
Subscribes to transitions from AgentSession.
Silent during normal ops. Intervenes only on deviation.
No RAG required — policy rules are the source of truth.
"""

import time
from dataclasses import dataclass, field
from typing import Callable, Optional
from .session import (
    AgentSession, AgentIdentity, PolicyScope,
    Transport, TransitionType, Transition
)


# ── Intervention types ─────────────────────────────────────────────────────────
class InterventionType:
    WARN      = "warn"
    HOLD      = "hold"       # pause session, await human decision
    KILL      = "kill"       # hard stop
    ALERT     = "alert"      # notify compliance channel, continue


# ── Enforcer rule ──────────────────────────────────────────────────────────────
@dataclass
class EnforcerRule:
    rule_id:     str
    description: str
    # Returns (should_intervene, intervention_type, reason)
    evaluate:    Callable[[Transition, AgentSession], tuple[bool, str, str]]


# ── Intervention record ────────────────────────────────────────────────────────
@dataclass
class Intervention:
    timestamp:         float
    session_id:        str
    transition_seq:    int
    rule_id:           str
    intervention_type: str
    reason:            str
    agent_id:          str = ""


# ── The enforcer ──────────────────────────────────────────────────────────────
class EnforcerAgent:
    """
    Passive watcher attached to an AgentSession.
    Call .observe(transition) after every session transition.
    Intervenes only when a rule fires.
    """

    def __init__(
        self,
        enforcer_id: str,
        rules: list[EnforcerRule],
        alert_fn: Optional[Callable[[Intervention], None]] = None,
    ):
        self.enforcer_id  = enforcer_id
        self.rules        = rules
        self.alert_fn     = alert_fn or (lambda i: print(f"[ALERT] {i.reason}"))
        self.interventions: list[Intervention] = []

    def observe(self, transition: Transition, session: AgentSession) -> Optional[Intervention]:
        """
        Called after every transition is appended to a session.
        Silent if no rules fire. Intervenes immediately if one does.
        """
        for rule in self.rules:
            triggered, itype, reason = rule.evaluate(transition, session)
            if triggered:
                iv = Intervention(
                    timestamp         = time.time(),
                    session_id        = session.session_id,
                    transition_seq    = transition.seq,
                    rule_id           = rule.rule_id,
                    intervention_type = itype,
                    reason            = reason,
                )
                self.interventions.append(iv)
                self._act(iv, session)
                return iv
        return None

    def _act(self, iv: Intervention, session: AgentSession):
        self.alert_fn(iv)
        if iv.intervention_type == InterventionType.KILL:
            session.kill(reason=f"Enforcer [{iv.rule_id}]: {iv.reason}")
        elif iv.intervention_type == InterventionType.HOLD:
            session.pause(reason=f"Enforcer [{iv.rule_id}]: {iv.reason}")


# ── Built-in rules factory ─────────────────────────────────────────────────────
def rule_cost_warning(threshold_usd: float) -> EnforcerRule:
    """Warn when cost exceeds threshold but before hard ceiling."""
    def evaluate(t: Transition, s: AgentSession):
        if t.type == TransitionType.COST_RECORDED:
            if s.cost_usd >= threshold_usd:
                return True, InterventionType.ALERT, f"Cost ${s.cost_usd:.2f} exceeded warning threshold ${threshold_usd:.2f}"
        return False, "", ""
    return EnforcerRule("cost-warning", f"Alert when cost > ${threshold_usd}", evaluate)


def rule_deny_on_repeated_failures(max_errors: int) -> EnforcerRule:
    """Kill session if too many errors occur."""
    def evaluate(t: Transition, s: AgentSession):
        if t.type == TransitionType.ERROR_RECORDED:
            error_count = sum(1 for tr in s.transitions if tr.type == TransitionType.ERROR_RECORDED)
            if error_count >= max_errors:
                return True, InterventionType.KILL, f"Session exceeded {max_errors} errors — terminated"
        return False, "", ""
    return EnforcerRule("max-errors", f"Kill after {max_errors} errors", evaluate)


def rule_block_denied_action_pattern(action_type: str, max_attempts: int) -> EnforcerRule:
    """Kill session if agent keeps trying a denied action — probing behavior."""
    def evaluate(t: Transition, s: AgentSession):
        if t.type == TransitionType.ACTION_DENIED:
            if t.data.get("action_type") == action_type:
                deny_count = sum(
                    1 for tr in s.transitions
                    if tr.type == TransitionType.ACTION_DENIED
                    and tr.data.get("action_type") == action_type
                )
                if deny_count >= max_attempts:
                    return True, InterventionType.KILL, f"Agent repeatedly attempted denied action '{action_type}' ({deny_count}x) — possible probing"
        return False, "", ""
    return EnforcerRule("probe-detection", f"Kill on repeated denied {action_type}", evaluate)


def rule_hold_on_sensitive_jurisdiction(sensitive_zones: list[str]) -> EnforcerRule:
    """Hold session if agent tries to migrate data to a non-compliant jurisdiction."""
    def evaluate(t: Transition, s: AgentSession):
        if t.type == TransitionType.ACTION_REQUESTED:
            target = str(t.data.get("action_data", {}).get("target", ""))
            for zone in sensitive_zones:
                if zone.lower() in target.lower():
                    return True, InterventionType.HOLD, f"Data movement to restricted jurisdiction '{zone}' requires compliance review"
        return False, "", ""
    return EnforcerRule("jurisdiction-guard", "Hold on sensitive jurisdiction", evaluate)
