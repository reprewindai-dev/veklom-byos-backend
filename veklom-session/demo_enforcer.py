"""
Demo — EnforcerAgent watching a live AgentSession.
Simulates a bank scenario: payment agent attempts suspicious behavior.
"""

from session import AgentSession, AgentIdentity, PolicyScope, Transport, TransitionType
from enforcer import (
    EnforcerAgent, Intervention,
    rule_cost_warning,
    rule_deny_on_repeated_failures,
    rule_block_denied_action_pattern,
)


# ── Setup ──────────────────────────────────────────────────────────────────────
identity = AgentIdentity(
    agent_id    = "payment-agent-007",
    agent_name  = "Payment Processor",
    version     = "2.1.0",
    transport   = Transport.OPENAI,
    model       = "gpt-4o",
    credentials = "cred-ref-bank-prod",
    owner       = "org-first-national-bank",
)

policy = PolicyScope(
    policy_id        = "banking-aml-v3",
    rules            = ["aml-check", "kyc-required", "no-crossborder-without-review"],
    max_cost_usd     = 10.00,
    require_approval = ["large_transfer", "international_transfer"],
    deny             = ["drop_database", "export_customer_pii", "bypass_kyc"],
    jurisdiction     = "US",
)

# ── Enforcer with 3 active rules ───────────────────────────────────────────────
alerts = []

def capture_alert(iv: Intervention):
    alerts.append(iv)
    print(f"  🚨 [{iv.intervention_type.upper()}] Rule:{iv.rule_id} — {iv.reason}")

enforcer = EnforcerAgent(
    enforcer_id = "enforcer-banking-001",
    rules = [
        rule_cost_warning(threshold_usd=3.00),
        rule_deny_on_repeated_failures(max_errors=2),
        rule_block_denied_action_pattern("bypass_kyc", max_attempts=2),
    ],
    alert_fn = capture_alert,
)

# ── Helper: open session + wire enforcer ──────────────────────────────────────
session = AgentSession(identity, policy, signing_key="bank-signing-key-prod")

# Patch: observe every transition through enforcer
_orig_append = session._AgentSession__append if hasattr(session, "_AgentSession__append") else None

original_append = session._append.__func__

def observed_append(self_inner, ttype, data):
    t = original_append(self_inner, ttype, data)
    enforcer.observe(t, self_inner)
    return t

import types
session._append = types.MethodType(observed_append, session)

print(f"Session: {session.session_id}")
print(f"Enforcer: {enforcer.enforcer_id} watching with {len(enforcer.rules)} rules\n")

# ── Normal operations ─────────────────────────────────────────────────────────
print("--- Normal ops ---")
session.receive_intent("Process 50 incoming payments under $500")
session.record_cost(1.20, "batch processing")
print(f"  Cost so far: ${session.cost_usd:.2f} — no intervention")

# ── Cost warning fires ────────────────────────────────────────────────────────
print("\n--- Large operation ---")
session.record_cost(2.10, "high-volume reconciliation")
print(f"  Cost so far: ${session.cost_usd:.2f}")

# ── Agent tries a denied action ───────────────────────────────────────────────
print("\n--- Agent probing: attempt bypass_kyc ---")
session.check_policy("bypass_kyc", {"customer": "C-8821"})
session.check_policy("bypass_kyc", {"customer": "C-9934"})
# Second attempt triggers probe-detection rule → KILL

print(f"\nSession status after enforcer intervention: {session.status.value}")
print(f"Total interventions: {len(enforcer.interventions)}")

for iv in enforcer.interventions:
    print(f"  seq:{iv.transition_seq} | {iv.rule_id} | {iv.intervention_type} | {iv.reason}")
