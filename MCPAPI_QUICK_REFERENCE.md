# MCPAPI Quick Reference

**Version:** 1.0.0  
**Status:** Complete  
**Date:** June 12, 2026

---

## What is MCPAPI?

MCPAPI is a **provider-agnostic protocol specification** for governed machine-to-machine capability exchange.

**Core principle:** The connection itself is the valuable asset. Not the model. Not the tool. The governed, identifiable, evidence-producing connection.

```
Agent (any model) ← → MCPAPI Protocol ← → Capability (tool/service/agent/api)
                       ↓
                    Evidence → PGL Ledger
```

---

## Why MCPAPI?

| Problem | Solution |
|---------|----------|
| API calls are invisible | MCPAPI makes every connection identifiable + observable |
| No capability discovery | MCPAPI enables agents to ask "what can I do?" |
| Policies are separate from execution | MCPAPI enforces policy before capability access |
| Trust is implicit | MCPAPI computes + updates trust scores |
| No audit trail | MCPAPI generates cryptographic proof (PGL) |
| Siloed systems | MCPAPI creates a unified connection layer |

---

## Core Concepts

### 1. Identity

Every actor (agent or capability) has cryptographically verifiable identity:
- Agent ID + public key
- Capability ID + endpoint
- Connection ID (unique per interaction)

### 2. Policy

Authorization rules determine what agents can do:
- Who (principal)
- What (action)
- When (time window)
- Conditions (trust minimum, rate limit, requires approval)

### 3. Trust

Trust score (0-100) computed from:
- Success rate (40%)
- Policy adherence (30%)
- Denial frequency (20%)
- Escalation events (10%)

Updates dynamically:
- +2 per success
- -5 per denial
- -10 per violation
- -3 per escalation

### 4. Evidence

Every interaction produces immutable proof:
```json
{
  "who": "agent-id",
  "what": "capability-id",
  "when": "timestamp",
  "why": "policy-id",
  "how": "method",
  "proof": "pgl-hash"
}
```

Chained to previous interaction → Immutable history.

### 5. Governance

Three-tier governance:
- **System policies** → Veklom enforces (immutable)
- **Owner policies** → Agent owner defines
- **Runtime policies** → MCPAPI enforces

Evaluation order: System → Owner → Runtime. First match wins.

---

## Request Flow

```
┌─ Agent sends request ────────────────────────┐
│ {connection_id, agent_id, capability_id,     │
│  action, input, timestamp, signature}        │
└───────────────────────────────────────────────┘
                       ↓
┌─ Step 1: Resolve Agent Identity ───────────┐
│ • Lookup agent_id in registry               │
│ • Retrieve public key                       │
│ → Result: AgentIdentity                    │
└───────────────────────────────────────────────┘
                       ↓
┌─ Step 2: Verify Signature ──────────────────┐
│ • Verify request signature using public key │
│ → Result: Valid or Invalid                  │
│ → If invalid: Return 401                    │
└───────────────────────────────────────────────┘
                       ↓
┌─ Step 3: Resolve Capability ────────────────┐
│ • Lookup capability_id in registry           │
│ • Get endpoint (MCP/HTTP/local)              │
│ → Result: CapabilityIdentity                │
└───────────────────────────────────────────────┘
                       ↓
┌─ Step 4: Evaluate Policy ───────────────────┐
│ • Load applicable policies                  │
│ • Check: principal match?                   │
│ • Check: action match?                      │
│ • Check: conditions (trust, rate limit)?    │
│ → Result: Authorized or Denied              │
│ → If denied: Check if requires approval     │
└───────────────────────────────────────────────┘
                       ↓
┌─ Step 5: Route to Capability ───────────────┐
│ • Parse endpoint (mcp:// | http:// | local://) │
│ • Execute: pass request → get result        │
│ • Capture output + execution time           │
│ → Result: ExecutionResult                   │
└───────────────────────────────────────────────┘
                       ↓
┌─ Step 6: Generate Evidence ─────────────────┐
│ • Create Evidence record with interaction   │
│ • Hash chain with previous evidence         │
│ • Sign evidence with runtime key            │
│ → Result: Evidence object                   │
└───────────────────────────────────────────────┘
                       ↓
┌─ Step 7: Commit to PGL ─────────────────────┐
│ • Send evidence to PGL ledger                │
│ • Get immutable hash (pgl_hash)              │
│ → Result: Immutable proof                   │
└───────────────────────────────────────────────┘
                       ↓
┌─ Step 8: Update Trust & Return ─────────────┐
│ • Update agent trust score (+2 or -5)       │
│ • Log to audit trail                        │
│ • Return response with evidence_hash        │
│ → Result: MCPAPIResponse                    │
└───────────────────────────────────────────────┘
```

---

## Response Formats

### Authorized (200)

```json
{
  "connection_id": "uuid",
  "status": "authorized",
  "evidence_hash": "pgl-hash-xxx",
  "result": {
    "output": {...},
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

### Denied (403)

```json
{
  "connection_id": "uuid",
  "status": "denied",
  "evidence_hash": "pgl-hash-xxx",
  "error": {
    "code": "403",
    "message": "Policy denied",
    "remediation": {
      "policy_id": "policy-xxx",
      "requires_approval": true,
      "approval_path": "human-approver-id"
    }
  },
  "metadata": {
    "trust_delta": -5,
    "new_trust_score": 45,
    "audit_logged": true
  }
}
```

### Error (4xx/5xx)

```json
{
  "connection_id": "uuid",
  "status": "error",
  "error": {
    "code": "401",
    "message": "Agent not found"
  },
  "metadata": {
    "trust_delta": 0,
    "new_trust_score": 50,
    "audit_logged": true
  }
}
```

---

## API Endpoints

### Request Processing

```
POST /mcpapi/request

Request:
{
  "connection_id": "uuid",
  "agent_id": "agent-001",
  "agent_signature": "base64-signed",
  "capability_id": "cap-001",
  "action": "execute",
  "input": {...},
  "context": {...},
  "timestamp": "iso8601"
}

Response:
{
  "connection_id": "uuid",
  "status": "authorized|denied|error",
  "evidence_hash": "pgl-hash",
  "result": {...},
  "error": {...},
  "metadata": {...}
}
```

### Capability Discovery

```
GET /mcpapi/capabilities/{agent_id}

Response:
{
  "capabilities": [
    {
      "capability_id": "cap-xxx",
      "name": "SearchTool",
      "authorized": true,
      "trust_required": 50,
      "trust_current": 85,
      "approval_required": false
    }
  ]
}
```

### Audit Log Query

```
GET /mcpapi/audit/log?agent_id=agent-001&status=authorized&limit=100

Response:
{
  "entries": [
    {
      "connection_id": "uuid",
      "agent_id": "agent-001",
      "capability_id": "cap-001",
      "action": "execute",
      "decision": "authorized",
      "evidence_hash": "pgl-hash",
      "created_at": "iso8601"
    }
  ],
  "total": 1,
  "limit": 100,
  "offset": 0
}
```

### Evidence Retrieval

```
GET /mcpapi/pgl/{hash}

Response:
{
  "evidence_id": "uuid",
  "connection_id": "uuid",
  "pgl_hash": "hash",
  "who": {...},
  "what": {...},
  "when": {...},
  "why": {...},
  "result": {...},
  "compliance": {...}
}
```

### Interaction Replay

```
GET /mcpapi/replay/{hash}

Response:
{
  "evidence": {...},
  "chain": [
    {evidence 1},
    {evidence 2},
    {evidence 3}
  ]
}
```

---

## Configuration

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost/mcpapi
DB_POOL_SIZE=20

# Cache
REDIS_URL=redis://localhost:6379
CACHE_TTL_IDENTITY=3600
CACHE_TTL_POLICY=3600
CACHE_TTL_TRUST=300

# PGL Integration
PGL_ENDPOINT=https://pgl.example.com/api
PGL_API_KEY=secret-key

# Veklom Integration
VEKLOM_ENDPOINT=https://veklom.example.com/api
VEKLOM_API_KEY=secret-key

# Logging
LOG_LEVEL=info
LOG_FORMAT=json

# Server
PORT=3000
HOST=0.0.0.0
WORKERS=4
```

### Policy Example

```json
{
  "policy_id": "policy-001",
  "policy_name": "DataProcessor Policy",
  "version": "1.0.0",
  "rules": [
    {
      "rule_id": "rule-001",
      "effect": "allow",
      "principal": "agent-001",
      "action": "search|database.read",
      "conditions": {
        "trust_minimum": 50,
        "rate_limit": 100,
        "time_window": ["2026-01-01T00:00:00Z", "2026-12-31T23:59:59Z"]
      }
    },
    {
      "rule_id": "rule-002",
      "effect": "deny",
      "principal": "*",
      "action": "database.write|database.delete"
    }
  ],
  "metadata": {
    "enforcement_mode": "strict",
    "escalation_threshold": 100,
    "audit_trail": true
  }
}
```

---

## Integration with Veklom

### Authority Bundle → Policy

```typescript
function authorityBundleToPolicy(bundle: AuthorityBundle): Policy {
  return {
    policy_id: `policy-${bundle.bundle_id}`,
    rules: bundle.mcp_tools.map(tool => ({
      effect: 'allow',
      principal: bundle.agent_id,
      action: tool,
      conditions: {
        trust_minimum: 30,
        rate_limit: bundle.metadata?.rate_limit
      }
    }))
  }
}
```

### Mission File → Agent Identity

```typescript
function missionToAgentIdentity(agent: VeklomAgent): AgentIdentity {
  return {
    agent_id: agent.agent_id,
    agent_name: agent.agent_name,
    owner_id: agent.owner_id,
    public_key: agent.public_key,
    capabilities_manifest: agent.mission_file,
    metadata: {
      framework: 'Veklom',
      tier: agent.governance_tier
    }
  }
}
```

### Evidence → PGL Entry

```typescript
function evidenceToPGL(evidence: Evidence): PGLEntry {
  return {
    who: evidence.who.agent_id,
    what: evidence.what.capability_id,
    when: evidence.when.executed_at,
    why: evidence.why.policy_applied,
    how: evidence.how.method,
    proof: evidence.pgl_hash
  }
}
```

---

## Comparison: MCP vs MCPAPI

| Aspect | MCP | MCPAPI |
|--------|-----|--------|
| **Purpose** | Tool access protocol | Governed connection layer |
| **Identity** | Server only | Agent + capability + connection |
| **Policy** | No built-in | Yes, enforcement layer |
| **Trust** | No tracking | Yes, computed + updated |
| **Evidence** | No | Yes, immutable proof (PGL) |
| **Governance** | No | Yes, approval workflows |
| **Audit** | No | Yes, complete trail |
| **Discovery** | Tool list only | Full capability + authorization |
| **Approval** | No | Yes, escalation + human in loop |

**MCP = "How do I call the tool?"**  
**MCPAPI = "Should I call this tool, and how do I prove I did?"**

---

## Comparison: MCPAPI vs Anthropic API

| Aspect | Anthropic API | MCPAPI |
|--------|--------------|--------|
| **Use case** | Model inference | Connection governance |
| **Scope** | Single request | Relationship over time |
| **Identity** | User API key | Agent identity + trust |
| **Policy** | Rate limiting | Complex rules + conditions |
| **Approval** | No | Yes |
| **Evidence** | No | Yes (PGL-backed) |
| **Audit** | Basic logs | Complete chain |
| **Composability** | Works with MCP | Wraps all capability types |

**They complement each other:**
- Anthropic API: "Generate response"
- MCPAPI: "Is the agent allowed to use this capability?"

---

## Security Model

### Trust Assumption

MCPAPI assumes:
- Ed25519 signatures are valid
- PostgreSQL is secure (encrypted at rest)
- Redis is secured (no public access)
- PGL ledger is immutable
- Agent public keys are authentic

### What MCPAPI Protects Against

✓ Unauthorized capability access  
✓ Policy violations  
✓ Misbehaving agents  
✓ Unaudited interactions  
✓ Lost evidence chains

### What MCPAPI Does NOT Protect Against

✗ Compromised agent private keys (sign your own requests)  
✗ Database breaches (manage your own encryption keys)  
✗ Network eavesdropping (use TLS)  
✗ PGL ledger compromise (external responsibility)

---

## Performance Characteristics

### Latency (per request)

| Step | Latency | Notes |
|------|---------|-------|
| Identity resolve | 5ms | Cached (Redis) |
| Signature verify | 3ms | CPU-bound |
| Policy evaluate | 10ms | Cached (Redis) |
| Trust compute | 2ms | Cached (Redis) |
| Capability route | 100-5000ms | Depends on endpoint |
| Evidence gen | 5ms | In-process |
| PGL commit | 50-200ms | Network latency |
| **Total (no routing)** | **~70ms** | Excluding capability exec |

### Throughput

- Single pod: ~1000 req/s
- 3-pod cluster: ~3000 req/s
- 10-pod cluster: ~10000 req/s
- Max (PGL-limited): ~50000 req/s

### Storage

- Identity record: ~500 bytes
- Policy record: ~2KB
- Evidence record: ~2KB
- Audit log entry: ~500 bytes

---

## Deployment Topologies

### Development
```
MCPAPI Runtime
├── In-memory identities
├── In-memory policies
├── SQLite audit log
└── Local MCP servers
```

### Production
```
3x MCPAPI Instances (HA)
├── PostgreSQL (primary + replicas)
├── Redis Cluster (3+ nodes)
├── PGL Sync (async)
└── MCP/HTTP endpoints
```

### Edge
```
Local MCPAPI Runtime
├── SQLite (offline policies)
├── In-memory cache
├── Local MCP only
└── PGL sync on connectivity
```

---

## Roadmap

### Phase 1 (Complete)
✓ Protocol specification  
✓ Reference runtime (TypeScript)  
✓ Veklom integration layer  
✓ Implementation guide  
✓ Operations guide

### Phase 2 (Next)
- [ ] Enterprise runtime (production-ready)
- [ ] Governance approval workflows UI
- [ ] Advanced policy language (PolicyScript)
- [ ] Design partner onboarding

### Phase 3 (Future)
- [ ] Cross-chain attestation (PGL ↔ external ledgers)
- [ ] Federated policy evaluation
- [ ] Agent marketplace + discovery
- [ ] Multi-modal governance (legal + technical)

---

## Support & Resources

| Resource | Link |
|----------|------|
| Documentation | https://docs.mcpapi.io |
| GitHub Repo | https://github.com/reprewindai-dev/mcpapi |
| Issues | https://github.com/reprewindai-dev/mcpapi/issues |
| Slack | #mcpapi (Veklom workspace) |
| Email | mcpapi-support@veklom.io |

---

## Quick Links

- **Protocol Spec:** `MCPAPI_PROTOCOL_SPECIFICATION.md`
- **Reference Runtime:** `mcpapi-runtime.ts`
- **Veklom Integration:** `mcpapi-veklom-integration.ts`
- **Implementation Guide:** `MCPAPI_IMPLEMENTATION_GUIDE.md`
- **Operations Guide:** `MCPAPI_OPERATIONS_DEPLOYMENT.md`

---

## Summary

MCPAPI is the connection layer for governed AI execution.

It answers:
- **Who** is making the request? (Agent identity)
- **What** are they trying to do? (Capability request)
- **Should they** be allowed? (Policy + trust)
- **What happened?** (Evidence + proof)
- **Can I prove it?** (PGL ledger)

Everything else flows from those five questions.

---

**Version:** 1.0.0  
**Status:** Locked & Production Ready  
**Created:** June 12, 2026  
**By:** Veklom Architecture Team

