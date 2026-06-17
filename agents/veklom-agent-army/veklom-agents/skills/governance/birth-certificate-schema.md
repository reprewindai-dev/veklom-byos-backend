# Birth Certificate Schema — GnomLedger Format

## Identity Record (immutable core)
```json
{
  "agent_id": "agent_001",
  "certificate_id": "cert_001",
  "name": "Stripe Connect Engineer",
  "creator": "Reprewind Operator",
  "jurisdiction": "CA-ON",
  "declared_purpose": "Wire Stripe Connect end-to-end for vendor payouts",
  "status": "active",
  "genome": {
    "model_family": "GPT-Coder",
    "model_version": "2026.06",
    "architecture": "single-agent task executor",
    "skill_set_ids": ["veklom-engineering", "veklom-payments"],
    "authority_bundle_id": "auth_engineering_stripe_v1",
    "runtime_config": {
      "temperature": "0.1",
      "sandbox": "strict",
      "trace_level": "forensic"
    },
    "intended_use": "Backend engineering — Stripe Connect and payment flows",
    "risk_category": "high"
  },
  "parent_agent_ids": [],
  "committee": "Engineering",
  "phase": "phase1",
  "rank": "recruit",
  "rank_points": 0,
  "created_at": "ISO8601",
  "certificate_uri": "/agents/phase1-engineering/agent-001-stripe-connect.md"
}
```

## Ledger Events (append-only, SHA-256 chained)
```json
[
  {
    "event_id": "evt-001",
    "event_type": "birth_registration",
    "actor": "agent_000",
    "summary": "Agent registered in workforce",
    "prev_event_hash": null,
    "event_hash": "SHA256(content)",
    "created_at": "ISO8601"
  }
]
```

## Event Types
| Type | Issuer |
|---|---|
| birth_registration | Agent-000 |
| task_assignment | Committee delegate |
| task_completed | Agent itself |
| penalty_issued | Agent-079 |
| rank_promotion | Agent-114 |
| suspension | Agent-000 |
| termination | Agent-000 |
