"""
Demo — AgentSession in action.
Simulates a real Veklom agent run: intent → policy → execution → audit.
"""

from session import (
    AgentSession, AgentIdentity, PolicyScope,
    Transport, SessionStatus
)
import json

# ── Identity ───────────────────────────────────────────────────────────────────
identity = AgentIdentity(
    agent_id    = "agent-001",
    agent_name  = "DepOps Agent",
    version     = "1.0.0",
    transport   = Transport.OPENAI,
    model       = "gpt-4o",
    credentials = "cred-ref-abc123",   # reference only, never the key
    owner       = "org-veklom-demo",
)

# ── Policy ─────────────────────────────────────────────────────────────────────
policy = PolicyScope(
    policy_id        = "policy-prod-strict",
    rules            = ["no-direct-db-write", "require-approval-deploy", "eu-data-only"],
    max_cost_usd     = 5.00,
    require_approval = ["deploy_code", "delete_record"],
    deny             = ["drop_database", "export_pii"],
    jurisdiction     = "EU",
)

# ── Open session ───────────────────────────────────────────────────────────────
session = AgentSession(identity, policy, signing_key="veklom-signing-key-prod")
print(f"Session opened: {session.session_id}")

# ── Agent receives intent ──────────────────────────────────────────────────────
session.receive_intent("Deploy latest build to production", source="user:admin")

# ── Plan compiled ──────────────────────────────────────────────────────────────
session.compile_plan({
    "steps": ["run_tests", "build_image", "deploy_code"],
    "target": "prod-cluster-eu",
})

# ── Policy check: allowed action ──────────────────────────────────────────────
allowed = session.check_policy("run_tests", {"suite": "integration"})
print(f"run_tests allowed: {allowed}")
if allowed:
    session.execute_action("run_tests", {"passed": 142, "failed": 0})
    session.record_cost(0.12, "test runner tokens")

# ── Policy check: requires approval ───────────────────────────────────────────
allowed = session.check_policy("deploy_code", {"target": "prod-cluster-eu", "version": "v2.4.1"})
print(f"deploy_code auto-allowed: {allowed}")  # False — needs human approval

# Human approves
session.approve_action("deploy_code", approved_by="user:sarah")
session.execute_action("deploy_code", {"status": "deployed", "version": "v2.4.1"})
session.record_cost(0.88, "deploy execution")

# ── Live policy injection mid-session ──────────────────────────────────────────
print("\nInjecting new policy mid-session...")
session.inject_policy(
    new_rules=["no-direct-db-write", "require-approval-deploy", "eu-data-only", "freeze-prod-writes"],
    injected_by="policy_engine:compliance-bot"
)

# ── Attempt denied action ──────────────────────────────────────────────────────
allowed = session.check_policy("drop_database", {"db": "users"})
print(f"drop_database allowed: {allowed}")  # False — always denied

# ── Close and get signed audit evidence ───────────────────────────────────────
record = session.close(outcome="success")

print(f"\n{'='*60}")
print(f"Session status:     {record.status}")
print(f"Total cost:         ${record.total_usd:.4f}")
print(f"Transitions logged: {len(record.transitions)}")
print(f"Chain hash:         {record.chain_hash[:32]}...")
print(f"Signature:          {record.signature[:32]}...")
print(f"Chain intact:       {session.verify_chain()}")
print(f"Signature valid:    {record.verify('veklom-signing-key-prod')}")
print(f"{'='*60}")

# ── Show transition log ────────────────────────────────────────────────────────
print("\nFull transition log:")
for t in record.transitions:
    print(f"  [{t['seq']:02d}] {t['type']:<30} {json.dumps(t['data'])[:60]}")

# Save audit record
with open("veklom-session/audit_record.json", "w") as f:
    f.write(record.to_json())
print("\nAudit record saved to audit_record.json")
