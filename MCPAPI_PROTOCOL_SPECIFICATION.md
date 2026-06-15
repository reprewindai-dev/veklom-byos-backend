# MCPAPI Protocol Specification

**Version:** 1.0.0  
**Status:** Locked  
**Author:** Veklom Architecture  
**Date:** June 12, 2026

---

## Executive Summary

MCPAPI is a provider-agnostic protocol specification for governed machine-to-machine capability exchange. It sits between agents (any inference provider) and capabilities (tools, services, APIs, databases, humans, sensors), ensuring every interaction carries identity, policy, trust, and evidence as first-class citizens.

**Core Thesis:**
The connection itself is the valuable asset. Not the model. Not the tool. The governed, identifiable, evidence-producing connection.

---

## Table of Contents

1. [Protocol Overview](#protocol-overview)
2. [Identity Model](#identity-model)
3. [Policy Model](#policy-model)
4. [Evidence Model](#evidence-model)
5. [Trust Model](#trust-model)
6. [Capability Discovery](#capability-discovery)
7. [Request/Response Contract](#requestresponse-contract)
8. [Error Handling](#error-handling)
9. [Audit Trail & Replay](#audit-trail--replay)
10. [Security Considerations](#security-considerations)

---

## 1. Protocol Overview

### 1.1 Design Principles

- **Provider Agnostic:** Works with Claude, GPT, Gemini, Llama, or any inference model
- **Connection First:** Every interaction is atomic and observable
- **Evidence Native:** All activity produces cryptographic proof (PGL-compatible)
- **Policy Enforcing:** Authorization happens before capability access
- **Deterministic:** Same input + policy = same outcome + same evidence

### 1.2 Architecture

```
┌─────────────────────────────────────────────┐
│ Agent (any inference provider)              │
├─────────────────────────────────────────────┤
│                                             │
│ MCPAPI Protocol Layer                       │
│  ├─ Identity Resolution                     │
│  ├─ Policy Enforcement                      │
│  ├─ Capability Routing                      │
│  ├─ Evidence Generation                     │
│  └─ Trust Computation                       │
│                                             │
├─────────────────────────────────────────────┤
│ Capability Layer (tool/service/agent/db)    │
├─────────────────────────────────────────────┤
│ PGL Ledger (identity + lineage proof)       │
└─────────────────────────────────────────────┘
```

### 1.3 Interaction Flow

```
Agent: "Execute capability X"
    ↓
MCPAPI: "Who are you?"
    → Identity resolution (agent_id lookup + validation)
    ↓
MCPAPI: "Are you authorized?"
    → Policy evaluation (capability + agent + context)
    ↓
MCPAPI: "What evidence exists?"
    → Trust computation (historical behavior + ratings)
    ↓
MCPAPI: "Route + Execute"
    → Capability invocation + result capture
    ↓
MCPAPI: "Generate proof"
    → PGL evidence hash + ledger entry
    ↓
Agent: Result + Evidence Hash
```

---

## 2. Identity Model

Every actor in MCPAPI must have cryptographically verifiable identity.

### 2.1 Agent Identity

```json
{
  "agent_id": "agent-uuid-v4",
  "agent_name": "string",
  "owner_id": "owner-uuid",
  "public_key": "ed25519-base64",
  "capabilities_manifest": "ipfs-hash",
  "created_at": "iso8601",
  "identity_proof": "signed-hash",
  "metadata": {
    "version": "string",
    "framework": "string",
    "inference_provider": "claude|gpt|gemini|llama|other",
    "tier": "system|user|service"
  }
}
```

### 2.2 Capability Identity

```json
{
  "capability_id": "capability-uuid-v4",
  "capability_name": "string",
  "provider_id": "provider-uuid",
  "endpoint": "mcp://provider/tool|http://api|local://path",
  "input_schema": "json-schema",
  "output_schema": "json-schema",
  "public_key": "ed25519-base64",
  "created_at": "iso8601",
  "version": "semver",
  "identity_proof": "signed-hash",
  "metadata": {
    "category": "tool|service|agent|database|human|sensor",
    "requires_approval": boolean,
    "cost": "carbon|credits|payment",
    "rate_limit": "requests-per-minute"
  }
}
```

### 2.3 Connection Identity

Every single interaction gets a unique connection ID:

```json
{
  "connection_id": "uuid-v4",
  "agent_id": "agent-uuid",
  "capability_id": "capability-uuid",
  "timestamp": "iso8601",
  "initiator": "agent",
  "trace_id": "parent-connection-id-if-nested"
}
```

### 2.4 Identity Resolution Process

1. Agent sends request with `agent_id` and signature
2. MCPAPI resolves `agent_id` from identity registry
3. MCPAPI validates signature against agent's public key
4. If valid: proceed to Policy Model
5. If invalid: deny + log security event

---

## 3. Policy Model

Policies determine what agents can do with what capabilities.

### 3.1 Policy Structure

```json
{
  "policy_id": "policy-uuid",
  "policy_name": "string",
  "version": "semver",
  "created_by": "owner-id",
  "created_at": "iso8601",
  "rules": [
    {
      "rule_id": "rule-uuid",
      "effect": "allow|deny",
      "principal": "agent-id|agent-role|*",
      "action": "capability-id|capability-category|*",
      "conditions": {
        "time_window": "iso8601-range",
        "rate_limit": "requests-per-minute",
        "requires_approval": boolean,
        "approval_path": "human-approver-id",
        "context_required": ["key1", "key2"],
        "trust_minimum": 50
      }
    }
  ],
  "metadata": {
    "enforcement_mode": "strict|warn|audit-only",
    "escalation_threshold": "number",
    "audit_trail": "on|off"
  }
}
```

### 3.2 Policy Evaluation

For each request:

1. **Principal Match:** Does the agent match the policy principal?
2. **Action Match:** Does the capability match the policy action?
3. **Condition Check:** Are all conditions satisfied?
4. **Effect Application:** Apply allow/deny effect
5. **Escalation:** If deny + high-trust agent, escalate to human

### 3.3 Default Policies

Every agent has three default policy buckets:

- **System Policy:** Veklom enforces this (cannot override)
- **Owner Policy:** Agent owner defines this
- **Runtime Policy:** MCPAPI runtime applies this

Evaluation order: System → Owner → Runtime. First match wins.

### 3.4 Approval Workflows

If `requires_approval: true`:

```
Agent requests capability
    ↓
MCPAPI: "This needs approval"
    ↓
Route to approval_path (human-approver-id)
    ↓
Human: "Approve" or "Deny"
    ↓
If Approve: Execute + generate evidence
If Deny: Log denial + return error
```

---

## 4. Evidence Model

Every interaction generates cryptographic proof stored in PGL.

### 4.1 Evidence Structure

```json
{
  "evidence_id": "uuid-v4",
  "connection_id": "uuid",
  "pgl_hash": "sha256-base64",
  "timestamp": "iso8601",
  "who": {
    "agent_id": "agent-uuid",
    "agent_public_key": "ed25519-base64",
    "owner_id": "owner-uuid"
  },
  "what": {
    "capability_id": "capability-uuid",
    "capability_name": "string",
    "action": "string"
  },
  "when": {
    "requested_at": "iso8601",
    "executed_at": "iso8601",
    "completed_at": "iso8601"
  },
  "why": {
    "policy_applied": "policy-id",
    "policy_version": "semver",
    "authorization_proof": "signed-hash",
    "request_context": "encrypted-json"
  },
  "how": {
    "method": "mcp|http|local",
    "endpoint": "string",
    "retry_count": "number"
  },
  "result": {
    "status": "authorized|denied|error",
    "output_hash": "sha256-base64",
    "output_size": "bytes",
    "execution_time_ms": "number"
  },
  "compliance": {
    "audit_logged": boolean,
    "regulatory_category": "string",
    "data_classification": "public|internal|confidential|restricted",
    "retention_policy": "string"
  }
}
```

### 4.2 Evidence Chain

Every evidence entry is hash-chained to the previous one:

```
Evidence #1: hash(who + what + when + result)
    ↓ (previous_hash)
Evidence #2: hash(who + what + when + result + previous_hash)
    ↓ (previous_hash)
Evidence #3: hash(who + what + when + result + previous_hash)
```

This produces an immutable replay log.

### 4.3 PGL Integration

Evidence is immediately committed to Project Genome Ledger:

```
MCPAPI generates evidence
    ↓
PGL: "Register this interaction"
    ↓
PGL creates: <who, what, when, proof>
    ↓
Returns: pgl_hash (immutable reference)
    ↓
MCPAPI stores pgl_hash in evidence
```

---

## 5. Trust Model

Trust is computed, not assumed.

### 5.1 Trust Scoring

```
trust_score = (0..100)

Factors:
  - Historical success rate (40%)
  - Policy adherence (30%)
  - Denial frequency (20%)
  - Escalation events (10%)

Formula:
trust_score = 
  (success_rate * 0.4) +
  (policy_adherence * 0.3) +
  (1 - denial_frequency * 0.2) +
  (1 - escalation_events * 0.1)
```

### 5.2 Trust Thresholds

Policies can require minimum trust:

```json
{
  "rule_id": "rule-uuid",
  "effect": "allow",
  "conditions": {
    "trust_minimum": 75
  }
}
```

If agent trust < threshold:
- Option 1: Deny
- Option 2: Require approval
- Option 3: Log and continue (audit mode)

### 5.3 Trust Lifecycle

```
Agent created: trust_score = 50 (neutral)
    ↓
Each successful execution: +2 points
    ↓
Each denied request: -5 points
    ↓
Each policy violation: -10 points
    ↓
Each escalation: -3 points
    ↓
Cap: 0 (minimum) to 100 (maximum)
    ↓
Decay: -1 point per month of inactivity
```

---

## 6. Capability Discovery

Agents need to know what they can access.

### 6.1 Capability Registry

Central registry of all capabilities:

```json
{
  "capabilities": [
    {
      "capability_id": "capability-uuid",
      "name": "string",
      "category": "tool|service|agent|database",
      "description": "string",
      "endpoint": "string",
      "input_schema": "json-schema-url",
      "output_schema": "json-schema-url",
      "requirements": {
        "minimum_trust": 50,
        "requires_approval": false,
        "cost": "free|credits|payment"
      },
      "provider": {
        "id": "provider-uuid",
        "name": "string"
      }
    }
  ]
}
```

### 6.2 Discovery Query

Agent queries: "What can I do?"

```json
{
  "agent_id": "agent-uuid",
  "query_type": "capabilities-for-agent"
}
```

MCPAPI returns:

```json
{
  "capabilities": [
    {
      "capability_id": "...",
      "name": "...",
      "authorized": true,
      "trust_required": 50,
      "trust_current": 85,
      "approval_required": false
    }
  ]
}
```

---

## 7. Request/Response Contract

### 7.1 Request Format

```json
{
  "connection_id": "uuid-v4",
  "agent_id": "agent-uuid",
  "agent_signature": "signed-request-hash",
  "capability_id": "capability-uuid",
  "action": "string",
  "input": {
    "params": {}
  },
  "context": {
    "trace_id": "parent-connection-id",
    "user_context": "optional-json",
    "audit_tags": ["tag1", "tag2"]
  },
  "timestamp": "iso8601"
}
```

### 7.2 Response Format (Success)

```json
{
  "connection_id": "uuid",
  "status": "authorized",
  "evidence_hash": "pgl-hash",
  "result": {
    "output": {},
    "output_hash": "sha256",
    "execution_time_ms": 150
  },
  "metadata": {
    "trust_delta": 2,
    "new_trust_score": 87,
    "audit_logged": true
  }
}
```

### 7.3 Response Format (Denied)

```json
{
  "connection_id": "uuid",
  "status": "denied",
  "reason": "policy_violation|trust_insufficient|requires_approval",
  "policy_id": "policy-uuid",
  "remediation": {
    "minimum_trust_required": 75,
    "trust_current": 50,
    "approval_required": true,
    "approval_path": "human-approver-id"
  },
  "evidence_hash": "pgl-hash"
}
```

---

## 8. Error Handling

### 8.1 Error Categories

| Error | Code | Action |
|-------|------|--------|
| Invalid Agent ID | 401 | Reject + log security event |
| Invalid Signature | 401 | Reject + log security event |
| Capability Not Found | 404 | Reject + suggest alternatives |
| Policy Denied | 403 | Reject + suggest approval path |
| Trust Insufficient | 403 | Reject + escalate to human |
| Rate Limited | 429 | Queue + retry + notify |
| Capability Error | 500 | Fail gracefully + generate evidence |
| Timeout | 504 | Retry up to 3x + log |

### 8.2 Retry Logic

```
Attempt 1: Execute
    ↓ (timeout)
Attempt 2: Retry (exponential backoff: 1s)
    ↓ (timeout)
Attempt 3: Retry (exponential backoff: 2s)
    ↓ (timeout)
Fail: Return 504 + generate failure evidence
```

### 8.3 Escalation

On policy denial with high-trust agent:

```
Policy: Deny
Agent trust: 85/100
    ↓
MCPAPI: "This is suspicious"
    ↓
Route to: security-team OR approval_path
    ↓
Human: Review + Approve OR Deny
    ↓
If approved: Execute + generate evidence
If denied: Log + return error
```

---

## 9. Audit Trail & Replay

### 9.1 Complete Audit Log

Every interaction is logged with:

```json
{
  "log_entry_id": "uuid",
  "timestamp": "iso8601",
  "connection_id": "uuid",
  "agent_id": "agent-uuid",
  "capability_id": "capability-uuid",
  "policy_applied": "policy-id",
  "decision": "authorized|denied|escalated",
  "evidence_hash": "pgl-hash",
  "user_context": "optional",
  "audit_tags": ["array"]
}
```

### 9.2 Replay Capability

From any evidence hash, reconstruct the interaction:

```
Query: /audit/replay/{evidence_hash}

Returns:
  - Full request
  - Policy evaluated
  - Decision made
  - Result produced
  - Next interaction in chain
```

### 9.3 Compliance Reporting

Export audit trail by:
- Date range
- Agent
- Capability
- Policy
- Status
- Data classification

---

## 10. Security Considerations

### 10.1 Signature Verification

Every request must be signed by the agent:

```
signature = Ed25519Sign(
  private_key = agent_private_key,
  message = SHA256(
    connection_id +
    agent_id +
    capability_id +
    action +
    input_json +
    timestamp
  )
)
```

MCPAPI verifies:

```
is_valid = Ed25519Verify(
  public_key = agent_public_key,
  message = SHA256(...),
  signature = request_signature
)
```

### 10.2 Encryption

Sensitive data (inputs/outputs) encrypted:

```
encrypted_input = AES256_GCM(
  key = capability_shared_secret,
  plaintext = input_json,
  associated_data = connection_id
)
```

### 10.3 Key Rotation

Agent keys rotated:
- On compromise detection
- Every 90 days
- On explicit request

Old keys maintained for 30 days for signature verification of historical requests.

### 10.4 Rate Limiting

Per-agent rate limits:

```
rate_limit = policy_specified OR default_10_requests_per_minute

tracked_by = agent_id + time_window

If exceeded:
  - Queue request
  - Return 429
  - Notify agent
  - Log event
```

### 10.5 Input Validation

All inputs validated against capability's input_schema:

```
is_valid = JSONSchema.validate(
  input = request_input,
  schema = capability_input_schema
)

If invalid:
  - Reject
  - Return validation errors
  - Log event
```

---

## Implementation Notes

### For Runtime Builders

Implement MCPAPI by:

1. **Identity Layer:** Store agent + capability identities + public keys
2. **Policy Engine:** Evaluate policies before execution
3. **Evidence Generator:** Produce evidence for every interaction
4. **PGL Client:** Commit evidence to Project Genome Ledger
5. **Trust Engine:** Compute and update trust scores
6. **Audit Logger:** Log all interactions immutably

### For Agent Developers

Use MCPAPI by:

1. **Register Identity:** Submit agent identity + public key
2. **Sign Requests:** Sign all requests with agent private key
3. **Query Capabilities:** Ask what you can access
4. **Execute:** Submit signed requests to MCPAPI
5. **Verify Evidence:** Check returned evidence_hash on PGL

### For Capability Providers

Register on MCPAPI by:

1. **Define Identity:** Create capability identity + schemas
2. **Expose Endpoint:** Provide mcp:// or http:// endpoint
3. **Set Metadata:** Cost, rate limits, categories
4. **Register Policy:** Define who can use this capability

---

## Versioning

- **Protocol Version:** 1.0.0
- **Changelog:** [link to versioning strategy]
- **Deprecation Policy:** 12-month notice before removal

---

## References

- Project Genome Ledger (PGL) Specification
- Model Context Protocol (MCP) Standard
- JSON Schema Specification
- OWASP Security Guidelines
- NIST Cryptography Standards

