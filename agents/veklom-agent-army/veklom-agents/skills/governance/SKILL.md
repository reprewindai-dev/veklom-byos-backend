---
name: veklom-governance
description: Governance, compliance, council voting, ledger management, and enforcement for Veklom sovereign agents. Load when managing council sessions, issuing penalties, reviewing compliance reports, writing birth certificates, or managing agent lifecycle.
metadata:
  version: 1.0.0
  committee: governance
  authority_bundle: auth_governance_v1
  linked_files:
    - council-protocol.md
    - penalty-matrix.md
    - birth-certificate-schema.md
---

# Veklom Governance Skill

## What This Skill Does
Governs the 120-agent workforce. Issues penalties, manages council votes, maintains the compliance ledger, and enforces GUARDRAILS.md.

## Repository Context
- Repo: reprewindai-dev/veklom-byos-backend | Server: 5.78.135.11
- Council ledger: docs/COUNCIL_LEDGER.md
- Compliance log: docs/COMPLIANCE_LOG.md
- GnomLedger: github.com/reprewindai-dev/gnomledger

## Core Actions

### Issue a Penalty
Append to docs/COMPLIANCE_LOG.md:
```json
{
  "agent_id": "agent-XXX",
  "guardrail": "CQ-08",
  "level": 3,
  "points_deducted": 20,
  "action": "priority_demotion",
  "issued_by": "agent-079",
  "timestamp": "ISO8601"
}
```

### Run a Council Vote
See council-protocol.md → load when running a session

### Register Agent (Birth Certificate)
See birth-certificate-schema.md → load when creating a new agent

### Check Penalty Levels
See penalty-matrix.md → load when determining penalty severity
