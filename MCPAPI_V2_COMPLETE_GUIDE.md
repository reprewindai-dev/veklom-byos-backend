# MCPAPI v2.0 Complete Guide

**Version:** 2.0.0  
**Status:** Complete & Locked  
**Date:** June 12, 2026  
**Layers:** Safety + Intelligence + Governance  

---

## What Changed from v1.0

MCPAPI v1.0 was a **connection audit layer** (prove what happened).

MCPAPI v2.0 is a **breach prevention system** (stop it from happening).

| Aspect | v1.0 | v2.0 |
|--------|------|------|
| Identity | Resolves agent | + Agent lifecycle management |
| Policy | Evaluates rules | + Policy composition + conflict detection |
| Trust | Tracks score | + Automatic suppression on anomalies |
| Evidence | Proves interaction | + Proof degradation tracking |
| **NEW:** Safety | None | Anomaly detection + quarantine + quorum approval |
| **NEW:** Intelligence | None | Cost attribution + behavioral learning + risk scoring |
| **NEW:** Governance | None | Temporal policies + delegation chains + effective perms |

---

## The Three Layers

### Layer 1: Safety Layer (Prevent Breaches)

**Goal:** Detect & stop malicious behavior before damage occurs.

**Components:**
1. **Behavioral Baseline Service** — Learn what's normal for each agent (first 30 days)
2. **Anomaly Detection Service** — Detect: request spikes, failure spikes, new capabilities, off-hours activity, delegation exploits
3. **Request Quarantine Service** — Hold suspicious requests for review
4. **Approval Quorum Service** — Require M-of-N signatures for high-risk requests
5. **Replay Attack Prevention Service** — Nonce-based + deduplication + signature time-locking
6. **Proof Degradation Service** — Track PGL proof integrity over time
7. **Agent Lifecycle Service** — Create → active → deactivated → archived → deleted with cascading revocation

**Key Protection:**
```
Request arrives
  ↓
Behavioral baseline: Is this normal?
  ├─ NO (anomaly) → Auto-suppress trust (−30 points)
  ├─ Critical anomaly → QUARANTINE (hold for approval)
  └─ YES → Continue
  
Approval quorum: Does it need approval?
  ├─ YES → Wait for 2-of-3 signatures (approvers must have trust ≥ 80)
  └─ NO → Continue
  
Execute → Generate evidence → Commit to PGL
```

---

### Layer 2: Intelligence Layer (Understand & Predict)

**Goal:** Understand what's happening, predict threats, attribute costs.

**Components:**
1. **Cost Attribution Service** — Track cost per agent/capability, enforce budgets, detect unusual spend
2. **Behavioral Learning Service** — Learn patterns: capability preferences, time-of-day patterns, failure types, collaboration partners
3. **Risk Scoring Service** — Calculate overall risk (0-100) from: trust, anomalies, costs, behaviors, violations
4. **Correlation Analysis Service** — Link multiple anomalies to detect coordinated attacks

**Key Insights:**
```
Agent's behavior over time:
  - Normally uses SearchTool (80% of requests) → Cost: 50 credits/day
  - Usually active 9-17 (business hours)
  - Failure rate: <1%
  - Collaborates with: Agent B, Agent C

Today's activity:
  - Using Database.delete (new!)
  - Active at 3 AM (unusual!)
  - Failure rate: 50%
  - Unusual cost spike: 500 credits
  - No collaboration requests

Correlation: All 4 anomalies detected simultaneously
  → Risk profile: RED (threat_level: critical)
  → Recommended action: Deactivate immediately + investigate
```

---

### Layer 3: Governance Layer (Compose Rules)

**Goal:** Merge policies from multiple sources into one executable rule.

**Components:**
1. **Policy Composition Engine** — Merge: system policy + owner policy + runtime policy + temporal adjustments
2. **Temporal Policy Engine** — Time-based policies: business hours vs after-hours, holidays, peak periods, seasons
3. **Delegation Chain Validator** — Track: who delegated to whom, how many hops, trust degradation per hop, max depth enforcement
4. **Effective Permissions Calculator** — Calculate: "What can this agent actually do right now?"

**Key Composition:**
```
System Policy (immutable):
  "All database writes require 2FA"

Owner Policy (flexible):
  "Agent can use SearchTool 100 times/day"

Runtime Policy (operational):
  "Rate limit: 50 req/min"

Temporal Adjustments:
  Business hours (9-17):   Trust required: 50, Rate limit: 100
  After hours (17-9):      Trust required: 75, Rate limit: 10
  Holidays:                Require approval for all requests

Effective result for NOW (3 PM Tuesday):
  - Can use SearchTool: YES
  - Rate limit: 100 req/min
  - Trust required: 50
  - Cost limit: $500/day
  - Requires approval: NO
  - Can delegate: YES (max 2 hops)
  - Expires: Tomorrow 17:00
```

---

## 9-Phase Request Processing (COMPLETE)

```
INCOMING REQUEST
        ↓
┌─────────────────────────────────────────┐
│ PHASE 1: IDENTITY & SECURITY            │
├─────────────────────────────────────────┤
│ • Resolve agent identity                │
│ • Verify signature (with time-locking)  │
│ • Check agent not deleted/suspended     │
│ • Detect replay attacks (nonce-based)   │
│ → If fails: Return 401/403              │
└─────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────┐
│ PHASE 2: CAPABILITY & POLICY            │
├─────────────────────────────────────────┤
│ • Resolve capability                    │
│ • Check capability not mutated          │
│ • Lookup delegation chain (if any)      │
│ • Compose policies (system+owner+temp)  │
│ • Detect policy conflicts               │
│ • Calculate effective permissions       │
│ → If denied: Return 403                 │
└─────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────┐
│ PHASE 3: SAFETY & ANOMALY DETECTION     │
├─────────────────────────────────────────┤
│ • Build/lookup behavioral baseline      │
│ • Detect behavioral anomalies           │
│ • Detect cost anomalies                 │
│ • Correlate multiple anomalies          │
│ • Auto-suppress trust if critical       │
│ • Quarantine if needed                  │
│ → If critical: HOLD FOR APPROVAL        │
└─────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────┐
│ PHASE 4: COST & BUDGET VALIDATION       │
├─────────────────────────────────────────┤
│ • Lookup cost model                     │
│ • Check daily/monthly budget            │
│ • Enforce overage policy                │
│ → If over-budget: Escalate or deny      │
└─────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────┐
│ PHASE 5: APPROVAL WORKFLOWS             │
├─────────────────────────────────────────┤
│ • Check if approval required            │
│ • Create approval quorum (M-of-N)       │
│ • Set escalation path                   │
│ • Return to caller: Wait for approval   │
│ → If approval required: HOLD             │
└─────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────┐
│ PHASE 6: EXECUTION                      │
├─────────────────────────────────────────┤
│ • Record pre-execution behavior         │
│ • Check rate limit (sliding window)     │
│ • Execute capability (MCP/HTTP/local)   │
│ • Capture result or error               │
│ → ~100-5000ms depending on capability   │
└─────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────┐
│ PHASE 7: EVIDENCE & PROOF               │
├─────────────────────────────────────────┤
│ • Generate evidence record              │
│ • Hash chain with previous              │
│ • Sign evidence                         │
│ • Commit to PGL ledger (async)          │
│ • Register proof degradation tracking   │
│ → Immutable proof of interaction        │
└─────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────┐
│ PHASE 8: AUDIT & COMPLIANCE             │
├─────────────────────────────────────────┤
│ • Record to Gnom ledger (Veklom)        │
│ • Update trust score (±2, ±3, ±5)      │
│ • Learn behavioral patterns             │
│ • Recalculate risk profile              │
│ → Continuous learning & adaptation      │
└─────────────────────────────────────────┘
        ↓
┌─────────────────────────────────────────┐
│ PHASE 9: RESPONSE                       │
├─────────────────────────────────────────┤
│ • Return success with evidence hash     │
│ • Include metadata:                     │
│   - trust_delta (±2, ±3, ±5)           │
│   - anomalies_detected (count)          │
│   - cost_attributed (credits)           │
│   - risk_score (0-100)                  │
│   - threat_level (green/yellow/orange)  │
└─────────────────────────────────────────┘
        ↓
     RESPONSE
```

---

## Decision Tree: What Happens at Each Stage

### PHASE 1: Signature Invalid?
```
Invalid signature
  ├─ Trust score: −5
  ├─ Log security event
  └─ Return 401 Unauthorized
```

### PHASE 2: Insufficient Trust?
```
Trust score < required
  ├─ Option A: Deny (if critical capability)
  ├─ Option B: Require approval (if moderate)
  └─ Option C: Continue with logging (if low-risk)
```

### PHASE 3: Anomalies Detected?
```
Anomaly severity: Critical
  ├─ Auto-suppress trust (−30 points)
  ├─ Quarantine request
  ├─ Create approval quorum (2-of-3)
  ├─ Set 1-hour hold deadline
  └─ Escalate to security team

Anomaly severity: High
  ├─ Log anomaly
  ├─ Alert monitoring
  ├─ Continue (but watch closely)
  └─ May require approval

Anomaly severity: Medium
  ├─ Log anomaly
  ├─ Increase monitoring threshold
  └─ Continue normally

Anomaly severity: Low
  ├─ Log anomaly
  └─ Continue normally
```

### PHASE 4: Budget Exceeded?
```
Overage policy: DENY
  ├─ Return 429 Too Many Credits
  └─ Suggest agent request budget increase

Overage policy: ESCALATE
  ├─ Route to finance team
  ├─ Await approval
  └─ If approved: Charge override fee

Overage policy: AUTO-CHARGE
  ├─ Execute request
  ├─ Charge from parent account
  └─ Alert finance (over-budget)
```

### PHASE 5: Approval Required?
```
Create quorum: 2-of-3 signatures
  ├─ Required approvers: [admin-001, admin-002, security-lead]
  ├─ Threshold: 2 approvals (within 1 hour)
  ├─ Approvers must have trust ≥ 80
  └─ Escalate to leadership if deadline passes
```

### PHASE 6: Execution Failed?
```
Capability execution error
  ├─ Trust score: −3 (minor penalty)
  ├─ Evidence: Still generated (proof of failure)
  ├─ Alert monitoring
  └─ Debug capability integration
```

### PHASE 7: PGL Down?
```
PGL unavailable (non-blocking)
  ├─ Evidence stored locally (PostgreSQL)
  ├─ Async retry every 30 seconds
  ├─ Continue processing normally
  └─ Sync to PGL when available (no data loss)
```

### PHASE 8: Risk Score RED?
```
Risk profile: RED (>75 risk score)
  ├─ Recommended actions:
  │   - Deactivate agent immediately
  │   - Lock all permissions
  │   - Initiate security investigation
  │   - Notify leadership
  └─ Status: Agent cannot execute until reviewed
```

---

## Data Models

### Request (Input)
```json
{
  "connection_id": "uuid",
  "agent_id": "agent-001",
  "agent_signature": "ed25519-base64",
  "capability_id": "search",
  "action": "execute",
  "input": {"query": "..."},
  "context": {
    "trace_id": "parent-conn-id",
    "user_context": {},
    "audit_tags": []
  },
  "timestamp": "iso8601"
}
```

### Response (Success)
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
    "audit_logged": true,
    "anomalies_detected": 0,
    "cost_attributed": 10,
    "risk_score": 25,
    "threat_level": "green"
  }
}
```

### Response (Quarantine)
```json
{
  "connection_id": "uuid",
  "status": "quarantined",
  "quarantine_id": "qr-xxx",
  "reason": "Critical anomalies detected",
  "requires_approval": true,
  "approvers_needed": 2,
  "approval_deadline": "iso8601",
  "anomalies": [
    {
      "type": "request_spike",
      "severity": "critical",
      "deviation_score": 3.5
    }
  ]
}
```

### Evidence (PGL-Bound)
```json
{
  "evidence_id": "uuid",
  "connection_id": "uuid",
  "pgl_hash": "hash-xxx",
  "timestamp": "iso8601",
  "who": {
    "agent_id": "agent-001",
    "agent_public_key": "base64",
    "owner_id": "owner-001"
  },
  "what": {
    "capability_id": "search",
    "capability_name": "SearchTool",
    "action": "execute"
  },
  "when": {
    "requested_at": "iso8601",
    "executed_at": "iso8601",
    "completed_at": "iso8601"
  },
  "why": {
    "policy_applied": "policy-id",
    "policy_version": "1.0.0",
    "authorization_proof": "signature",
    "request_context": "encrypted"
  },
  "how": {
    "method": "mcp",
    "endpoint": "mcp://server/tool",
    "retry_count": 0
  },
  "result": {
    "status": "authorized",
    "output_hash": "sha256",
    "output_size": 1024,
    "execution_time_ms": 150
  },
  "compliance": {
    "audit_logged": true,
    "regulatory_category": "standard",
    "data_classification": "internal",
    "retention_policy": "90-days"
  },
  "previous_hash": "chain-to-previous"
}
```

---

## Operational Playbook

### Scenario 1: Normal Request (Low Risk)
```
Request: Agent-001 → SearchTool
  Phase 1: Signature valid ✓
  Phase 2: Policy allows ✓
  Phase 3: No anomalies ✓
  Phase 4: Budget OK ✓
  Phase 5: No approval needed ✓
  Phase 6: Execute (120ms) ✓
  Phase 7: Evidence → PGL ✓
  Phase 8: Trust +2, log entry ✓
  Phase 9: Return success
  
Result: Approved in 150ms
Trust: 87/100
Risk: Green
```

### Scenario 2: Suspicious Pattern (High Risk)
```
Request: Agent-001 → Database.delete (UNUSUAL!)
  Phase 1: Signature valid ✓
  Phase 2: Policy allows (but unusual)
  Phase 3: ANOMALIES DETECTED:
    - New capability (database.delete never used before)
    - Off-hours activity (3 AM)
    - Cost spike (500 credits vs. normal 10)
    Severity: CRITICAL
    → Auto-suppress trust (−30 points, now 55)
    → Quarantine request
  Phase 5: Require approval quorum
    - Need 2-of-3: [admin-001, admin-002, security-lead]
    - Deadline: 1 hour
  Phase 9: Return QUARANTINED
  
Result: Held for review
Approvals: 0/2
Deadline: 2026-06-12 16:47 UTC
Risk: RED (75+)
```

### Scenario 3: Replay Attack (Security)
```
Request: Agent-001 → SearchTool
  Phase 1: Check nonce
    - Nonce: "abc123..."
    - Already used? YES!
    - This is a REPLAY ATTACK
    → Trust −10 (suspected compromise)
    → Log security event
    → Block request
  Phase 9: Return 403 Forbidden
  
Result: Blocked
Reason: Replay attack detected
Trust: 37/100 (compromised)
Alert: Security team (HIGH)
Recommended: Deactivate agent + rotate keys
```

### Scenario 4: Approval Granted
```
Quarantine: qr-001 (database.delete request)
  
Admin-001 signs: "approve" (signature-001)
  Trust: 92/100 ✓ (sufficient)
Admin-002 signs: "approve" (signature-002)
  Trust: 88/100 ✓ (sufficient)
  
Quorum reached: 2-of-2 ✓

Action:
  → Execute original request
  → Generate evidence (with approval proof)
  → Trust −5 (unusual behavior, but approved)
  → Log approval chain in evidence
  
Result: Approved + Executed
Approvals: [admin-001, admin-002]
Evidence: Contains approval signatures
Trust: 50/100 (penalized for unusual activity)
```

---

## Monitoring Dashboards

### Dashboard 1: System Health
```
Overall Status: HEALTHY
  - Requests/sec: 850 (target: 1000)
  - P95 latency: 120ms (target: 150ms)
  - Error rate: 1.2% (target: <5%)
  - PGL sync: ✓ (no backlog)

Agents
  - Active: 247
  - Deactivated: 12
  - Risk: RED: 2, ORANGE: 8, YELLOW: 34, GREEN: 203

Approval Queue
  - Pending: 4
  - Overdue: 1 (escalate!)
  - Approved today: 23
  - Denied: 2
```

### Dashboard 2: Security & Anomalies
```
Today's Activity
  - Anomalies detected: 47
    • Critical: 2
    • High: 8
    • Medium: 15
    • Low: 22
  
  - Correlation patterns: 3
    • Agent-001: Request spike + cost spike (concurrent)
    • Agent-047: Off-hours behavior (unusual, but normal)
    • Agents-103,104: Collaboration pattern (expected)

  - Replays blocked: 1
  - Policy violations: 0
  - Deactivations: 2
```

### Dashboard 3: Cost Attribution
```
Daily Spend
  - Total: $4,230 (budget: $5,000)
  - By capability:
    • SearchTool: $2,100 (top cost)
    • Database.read: $1,230
    • Translation: $650
    • Other: $250

  - By agent:
    • Agent-001: $890
    • Agent-047: $750
    • ... (rest < $500)

  - Anomalies: 3
    • Agent-056: 10x normal spend
    • Agent-078: Using new capability (expensive)
```

### Dashboard 4: Trust Scores
```
Trust Distribution
  - >80: 180 agents (GREEN, low monitoring)
  - 60-80: 45 agents (YELLOW, elevated monitoring)
  - 40-60: 18 agents (ORANGE, active monitoring)
  - <40: 4 agents (RED, restricted)

Trust Trends
  - Avg trust: 72/100 (stable)
  - Biggest gainers: Agent-089 (+15), Agent-055 (+12)
  - Biggest losers: Agent-001 (−30), Agent-056 (−25)

Decay Schedule
  - Monthly decay: −1 point per month (inactivity)
  - Last decay: 2 days ago
  - Next decay: 28 days from now
```

---

## Deployment Checklist

### Week 1: Foundation
- [ ] Deploy PostgreSQL + Redis
- [ ] Load MCPAPI v1.0 code
- [ ] Verify core pipeline works
- [ ] Set up basic monitoring (Prometheus)

### Week 2: Safety Layer
- [ ] Implement behavioral baseline service
- [ ] Deploy anomaly detection
- [ ] Set up request quarantine
- [ ] Test approval quorum flows
- [ ] Deploy replay prevention

### Week 3: Intelligence Layer
- [ ] Implement cost attribution
- [ ] Deploy behavioral learning
- [ ] Set up risk scoring
- [ ] Deploy correlation analysis
- [ ] Create intelligence dashboards

### Week 4: Governance Layer
- [ ] Implement policy composition
- [ ] Deploy temporal policies
- [ ] Set up delegation chains
- [ ] Deploy effective permissions calculator
- [ ] Create governance dashboards

### Week 5: Integration & Testing
- [ ] Wire all three layers into runtime
- [ ] End-to-end testing (9 phases)
- [ ] Load testing (1000 req/s)
- [ ] Security audit
- [ ] Incident response drills

### Week 6: Monitoring & Operations
- [ ] Deploy Grafana dashboards
- [ ] Set up alerting (Prometheus → PagerDuty)
- [ ] Create runbooks (incident response)
- [ ] SLA definition (99.9% uptime)
- [ ] On-call rotation setup

### Week 7: Design Partner Onboarding
- [ ] Select 3-5 design partners
- [ ] Provide API keys
- [ ] Document API
- [ ] Set up dedicated support
- [ ] Weekly feedback sessions

### Week 8: Production Deployment
- [ ] Blue-green deployment (zero downtime)
- [ ] Canary rollout (5% → 25% → 50% → 100%)
- [ ] Monitor error rates (should stay <1%)
- [ ] Document lessons learned
- [ ] Handoff to operations team

---

## Success Metrics

### By Week 8
- [ ] 100% of requests processed (v1.0 + v2.0 layers)
- [ ] <5% error rate (including anomalies caught)
- [ ] P95 latency: <150ms (excluding capability execution)
- [ ] 3-5 design partners live
- [ ] 0 security incidents
- [ ] Cost attribution: 100% accuracy
- [ ] Risk scoring: Validated against actual incidents
- [ ] Documentation: Complete + tested

### By Month 3
- [ ] 50 design partners live
- [ ] $100K MRR (if monetized)
- [ ] 2 strategic partnerships (capability providers)
- [ ] <1% false positive rate (anomalies)
- [ ] 99.5% availability (SLA met)
- [ ] 10,000 req/s sustained throughput
- [ ] Zero PGL evidence lost (proof integrity 100%)

---

## File Reference

**Core Protocol & v1.0:**
- `MCPAPI_PROTOCOL_SPECIFICATION.md`
- `mcpapi-runtime.ts`
- `mcpapi-veklom-integration.ts`

**v2.0 Enhanced Layers:**
- `mcpapi-safety-layer.ts` (1000+ lines)
- `mcpapi-intelligence-layer.ts` (900+ lines)
- `mcpapi-governance-layer.ts` (1000+ lines)
- `mcpapi-enhanced-runtime.ts` (400+ lines, integrates all)

**Guides:**
- `MCPAPI_IMPLEMENTATION_GUIDE.md`
- `MCPAPI_OPERATIONS_DEPLOYMENT.md`
- `MCPAPI_QUICK_REFERENCE.md`

---

## Conclusion

MCPAPI v2.0 is a **complete breach prevention + audit system**.

It answers 12 critical questions for every single request:

1. Who is making this request? (Identity)
2. Is the signature valid? (Security)
3. Is this agent compromised? (Lifecycle)
4. What capability are they requesting? (Resolution)
5. Has the capability been modified? (Mutation detection)
6. Is this delegated? (Lineage)
7. What policies apply? (Composition)
8. Do policies conflict? (Resolution)
9. Are the permissions effective? (Calculation)
10. Is the behavior anomalous? (Anomaly detection)
11. Should this be quarantined? (Safety)
12. Was it approved? (Quorum)
13. Did it execute? (Result)
14. What proof exists? (Evidence)
15. Who gets blamed/credited? (Attribution)

**Every request is:**
- Verified (signature + nonce)
- Authorized (policy + trust + approval)
- Observed (anomaly + cost + behavior)
- Executed (with error handling)
- Proven (PGL-backed evidence)
- Audited (with full compliance trail)
- Learned from (patterns + risk)

**This is production-grade breach prevention for AI agents.**

