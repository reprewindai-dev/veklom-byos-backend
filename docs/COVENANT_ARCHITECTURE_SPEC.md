# Veklom Covenant Architecture: Complete Implementation Reference
## The 9-Phase Lifecycle, Trust Connection Schema, CAPPO Policy Layer, and the Agentic Edge

> **Context:** This document synthesizes the Gemini Agent-Driven Architecture research with Veklom's
> Covenant model, BYOS backend docs (SYSTEM_MAP, WIRING_MATRIX, VABP, CAPI_HOST_VALIDATION,
> SEMANTIC_STEWARDSHIP), and the OpenAPI route inventory. It is a build specification, not a
> summary. Every section maps to what must be implemented.

---

## Part I — The Veklom Thesis in One Sentence

Veklom's Covenant is the governed, cryptographically attested version of what Gemini's research
calls "autonomous agent directly hitting the data layer." The difference: Veklom adds PGL identity,
CAPPO policy enforcement, VNP measurement evidence, and x402 economic settlement to every
hop — making the middleware evaporation safe for enterprise M2M.

Traditional REST: `Agent → HTTP endpoint → middleware → DB`
Agentic bare-GraphQL: `Agent → GraphQL → RLS → DB`
Veklom Covenant: `Agent[PGL-DID] → Covenant[CAPPO policy] → API[VNP-measured] → settlement[x402]`

---

## Part II — The 9-Phase Covenant Lifecycle Dashboard

Each phase has a canonical state name (from SEMANTIC_STEWARDSHIP), a trigger, backend route(s),
data emitted, and a dashboard display contract. The dashboard must never hardcode phase status —
every badge derives from a backend capability/status manifest.

---

### Phase 0 — DISCOVERY

**What happens:** An autonomous agent (or human principal) invokes the Veklom introspection
endpoint. The system returns a machine-readable map of every available API connection: provider,
endpoint, region, VNP score, CAPPO policy requirements, x402 payment terms, and current
availability state.

**Trigger:** `GET /api/v1/connections/discovery` or `GET /api/v1/marketplace/apis`

**WIRING_MATRIX status:** Partially wired. The marketplace listing route exists but does not yet
return VNP scores, CAPPO policy requirements, or x402 terms inline.

**Data emitted (target schema):**
```json
{
  "discovery_id": "uuid",
  "agent_did": "did:veklom:...",
  "timestamp": "ISO8601",
  "available_connections": [
    {
      "api_id": "uuid",
      "provider": "string",
      "base_url": "string",
      "vnp_score": "number | null",
      "vnp_evidence_count": "integer",
      "cappo_policy_id": "uuid",
      "cappo_required_clearances": ["string"],
      "x402_payment_required": "boolean",
      "x402_asset": "USDC | ETH | null",
      "x402_amount_per_call": "number | null",
      "availability_state": "Live | Config Incomplete | Insufficient Evidence | Methodology Target",
      "regions": ["Ashburn", "Hillsboro", "Nuremberg", "Falkenstein", "Singapore"]
    }
  ]
}
```

**Dashboard display:** "DISCOVERY" badge (teal). Shows count of available APIs, map of active
regions, VNP score distribution. Zero-score APIs show "Insufficient Evidence", not a number.

---

### Phase 1 — IDENTITY RESOLUTION

**What happens:** The agent presents its cryptographic identity (PGL DID + Ed25519 signature).
The backend resolves the DID against the PGL registry, retrieves the agent's governed runtime
profile (CAPPO), and establishes the session principal.

**Trigger:** `POST /api/v1/auth/pgl-resolve` → returns session token with embedded claims

**WIRING_MATRIX status:** BACKEND-MISSING. The `pgl_client.py` returns fake UUIDs.
This is P0. Nothing downstream is trustworthy until this resolves to a real PGL record.

**Data emitted:**
```json
{
  "resolution_id": "uuid",
  "agent_did": "did:veklom:agent:<hash>",
  "principal_did": "did:veklom:principal:<hash>",
  "pgl_record": {
    "registered_at": "ISO8601",
    "governance_profile_id": "uuid",
    "clearance_level": "string",
    "active_delegations": ["uuid"]
  },
  "session_token": "JWT with embedded PGL claims",
  "session_expires": "ISO8601",
  "identity_verified": true
}
```

**Dashboard display:** "IDENTITY VERIFIED" badge (green) or "PGL UNRESOLVED" (red).
Show DID fragment, clearance level, governance profile name.

---

### Phase 2 — POLICY EVALUATION (CAPPO)

**What happens:** CAPPO evaluates whether this agent/principal combination is permitted to
initiate a connection to the requested API under the governing policy. Policy checks include:
clearance level, rate limits, allowed endpoints, cost ceiling, data classification, jurisdiction
constraints, and safety gates.

**Trigger:** `POST /api/v1/cappo/evaluate` with `{agent_did, api_id, endpoint, method}`

**WIRING_MATRIX status:** Routes exist (`/api/v1/governed/*`) but CAPPO evaluation is not
wired to real PGL-backed policy enforcement. Returns permissive defaults.

**CAPPO policy object (canonical schema):**
```json
{
  "policy_id": "uuid",
  "policy_version": "semver",
  "api_id": "uuid",
  "governing_principal_did": "did:veklom:...",
  "clearance_required": ["L1", "L2"],
  "allowed_endpoints": ["/v1/chat/completions", "/v1/embeddings"],
  "denied_endpoints": ["/v1/admin/*"],
  "rate_limit": { "calls_per_minute": 60, "calls_per_day": 10000 },
  "cost_ceiling_usd": 100.00,
  "data_classification_allowed": ["INTERNAL", "PUBLIC"],
  "jurisdiction_restrictions": ["CA", "US"],
  "safety_gates": {
    "require_vnp_score_minimum": 750,
    "require_vnp_evidence_minimum": 10,
    "require_signed_observations": true
  },
  "evaluation_result": "APPROVED | DENIED | CONDITIONAL",
  "denial_reason": "string | null",
  "conditions": ["string"]
}
```

**Dashboard display:** "POLICY APPROVED" (green) / "POLICY DENIED" (red) / "CONDITIONAL" (amber).
Show which gates passed/failed. Show cost ceiling consumed.

---

### Phase 3 — VNP TRUST SCORE GATE

**What happens:** Before connection is authorized, the system checks the target API's live VNP
score against the CAPPO-specified minimum. This is where measurement evidence becomes a
first-class access control gate — not a display metric.

**Trigger:** `GET /api/v1/vnp/score/{api_id}` called internally during CAPPO evaluation

**WIRING_MATRIX status:** Scoring returns `100` as default when no evidence exists.
This is a critical truthfulness failure. No evidence MUST return `null` + state
`insufficient_evidence`. The CAPPO gate should DENY connection when evidence_count < minimum.

**Score gate object:**
```json
{
  "api_id": "uuid",
  "score": "number | null",
  "state": "Live | Insufficient Evidence | Config Incomplete",
  "evidence_count": "integer",
  "evidence_window_hours": 24,
  "p50_ms": "number | null",
  "p95_ms": "number | null",
  "availability_pct": "number | null",
  "semantic_pass_rate": "number | null",
  "signed_observation_pct": "number | null",
  "region_coverage": ["Ashburn", "Hillsboro"],
  "score_version": "semver",
  "gate_result": "PASS | FAIL | BYPASS_INSUFFICIENT_DATA",
  "gate_minimum": 750
}
```

**Dashboard display:** Score gauge (0–1000). Pillar breakdown bars. Region coverage dots.
Evidence count prominently. "GATE PASSED" or "GATE FAILED — score below minimum."

---

### Phase 4 — CONNECTION INSTANTIATION

**What happens:** A Trust Connection object is created in the database. This is the canonical
record binding: agent identity + principal + target API + governing CAPPO policy + VNP score
snapshot + x402 payment authorization. The connection has a unique ID used in all downstream
telemetry, billing, and settlement.

**Trigger:** `POST /api/v1/connections` → returns `connection_id`

**WIRING_MATRIX status:** Connection creation routes exist but do not persist the full
Trust Connection schema (see Part IV below for complete schema).

**Lifecycle states at instantiation:**
- `INITIALIZING` → being constructed
- `PENDING_PAYMENT` → x402 payment challenge issued
- `ACTIVE` → payment confirmed, connection live
- `SUSPENDED` → policy violation detected mid-session
- `TERMINATED` → graceful close
- `FAILED` → unrecoverable error
- `REVOKED` → forced close by CAPPO governance event

**Dashboard display:** Connection card. Show state badge. Show bound API, agent DID,
policy version, VNP score at connection time, x402 payment status.

---

### Phase 5 — x402 PAYMENT & ECONOMIC SETTLEMENT

**What happens:** If the API requires x402 payment, the backend issues a payment challenge.
The agent's x402 client resolves the challenge, signs a payment authorization, and the backend
verifies the payment receipt before releasing the connection to ACTIVE state.

**Trigger:** `POST /api/v1/x402/challenge` → agent pays → `POST /api/v1/x402/verify`

**WIRING_MATRIX status:** x402 routes are real but `verify` compares stored hashes and
application-secret-derived signatures. Not on-chain verification. The settlement state must
expose exact achieved stage (see below), never generic "Connected."

**x402 settlement state machine:**
```
Not Configured
  → Configured
    → Payment Challenge Issued
      → Receipt Persisted
        → On-Chain Verification Working
          → Settlement Confirmed
            → SLA Slashing Capability Working (Methodology Target)
```

**Evidence required per stage:**
- "Settlement Confirmed": network, chain_id, tx_hash, block_number, confirmation_count,
  receipt_id, amount, asset, payee, verifier_result, timestamp
- Never show "Connected" without all fields populated from a real receipt.

**Dashboard display:** Stage indicator showing current achieved stage. Amount paid.
Asset type. Receipt ID. On-chain verification state. Not "Connected" — the exact stage name.

---

### Phase 6 — GOVERNED EXECUTION

**What happens:** The connection is ACTIVE. The agent executes API calls through Veklom's
governed proxy. Every call is logged with: request hash, response hash, latency phases
(DNS/TCP/TLS/TTFB/total), HTTP status, semantic assertion result, cost consumed vs. ceiling,
and the connection_id binding the call to the full Covenant chain.

**Trigger:** Proxied calls through `POST /api/v1/governed/execute` or direct BYOS proxy

**WIRING_MATRIX status:** Governed execution routes exist but do not capture all required
telemetry fields. DNS/TCP/TLS/TTFB phase timing is not collected. Semantic assertions are
not evaluated per call.

**Per-call telemetry record:**
```json
{
  "execution_id": "uuid",
  "connection_id": "uuid",
  "agent_did": "did:veklom:...",
  "api_id": "uuid",
  "endpoint": "string",
  "method": "GET | POST | ...",
  "request_hash": "sha256:...",
  "response_hash": "sha256:...",
  "started_at": "ISO8601",
  "dns_ms": "number | null",
  "tcp_ms": "number | null",
  "tls_ms": "number | null",
  "ttfb_ms": "number | null",
  "total_ms": "number",
  "http_status": "integer",
  "transport_reachable": "boolean",
  "semantic_assertion_passed": "boolean | null",
  "cost_usd": "number",
  "cost_ceiling_remaining_usd": "number",
  "cappo_policy_violated": "boolean",
  "violation_type": "string | null",
  "probe_node_id": "uuid | null",
  "region": "string"
}
```

**Dashboard display:** Live call log. Latency timeline (DNS→TCP→TLS→TTFB→total waterfall).
Cost meter. Semantic pass/fail rate. Policy violation alerts.

---

### Phase 7 — CONTINUOUS SAFETY MONITORING

**What happens:** CAPPO monitors the running connection continuously. Safety gates check:
cost ceiling approach, anomalous latency spikes, semantic failure rate increase, rate limit
approach, policy drift events. The connection can transition to SUSPENDED without terminating.

**Trigger:** Background CAPPO monitor; event-driven from execution telemetry stream

**WIRING_MATRIX status:** BACKEND-MISSING for continuous monitoring. No background monitor
process for live connections. Safety checks happen only at connection instantiation.

**Safety event types:**
- `COST_CEILING_WARNING` (80% of ceiling consumed)
- `COST_CEILING_BREACH` (100% — connection SUSPENDED)
- `LATENCY_DEGRADATION` (p95 > 3× baseline)
- `SEMANTIC_FAILURE_SPIKE` (>10% semantic failures in rolling window)
- `RATE_LIMIT_APPROACH` (80% of rate limit consumed)
- `POLICY_DRIFT` (CAPPO policy updated mid-session)
- `VNP_SCORE_DROP` (live score drops below gate minimum)
- `PROVIDER_INCIDENT` (VNP measurements from multiple regions fail simultaneously)

**Dashboard display:** Live event stream. Connection health indicator. Suspend/Resume controls.
Alert history with timestamps and resolution status.

---

### Phase 8 — TERMINATION & PROOF GENERATION

**What happens:** The connection closes (graceful, policy-forced, or error). The backend
generates a Covenant Proof — a signed, append-only record of the entire lifecycle:
PGL identity → CAPPO policy → VNP score gate → x402 settlement → execution telemetry →
safety events → final state. This proof is submitted to PGL/gnomledger for attestation.

**Trigger:** `POST /api/v1/connections/{id}/terminate` or automatic on lifecycle completion

**WIRING_MATRIX status:** Termination routes exist but Covenant Proof generation is
BACKEND-MISSING. PGL attestation submission is BACKEND-MISSING.

**Covenant Proof object:**
```json
{
  "proof_id": "uuid",
  "connection_id": "uuid",
  "generated_at": "ISO8601",
  "lifecycle_summary": {
    "phase_0_discovery_at": "ISO8601",
    "phase_1_identity_verified": "boolean",
    "phase_2_policy_approved": "boolean",
    "phase_3_vnp_gate_passed": "boolean",
    "phase_4_instantiated_at": "ISO8601",
    "phase_5_payment_settled": "boolean",
    "phase_5_receipt_id": "string | null",
    "phase_6_calls_made": "integer",
    "phase_6_semantic_pass_rate": "number",
    "phase_6_cost_total_usd": "number",
    "phase_7_safety_events": ["event_type"],
    "phase_8_final_state": "TERMINATED | FAILED | REVOKED"
  },
  "canonical_hash": "sha256 of ordered lifecycle fields",
  "signed_by": "did:veklom:backend:<node_id>",
  "signature": "Ed25519:...",
  "pgl_attestation_id": "uuid | null",
  "pgl_attestation_tx": "string | null"
}
```

**Dashboard display:** Proof card with hash. Download proof JSON. PGL attestation status.
Share proof URL. VNP badge eligibility derived from proof.

---

## Part III — Covenant vs. Traditional REST API Governance

| Dimension | Traditional REST Governance | Veklom Covenant |
|-----------|----------------------------|-----------------|
| **Identity model** | API key or OAuth token; stateless per-request | PGL DID; persistent cryptographic identity across all sessions |
| **Authorization layer** | Middleware checks JWT claims; application code | CAPPO policy object with versioned rules; policy is a first-class database record |
| **Security perimeter** | Application server validates and filters | PostgreSQL RLS + CAPPO policy + VNP score gate; database IS the firewall |
| **Trust basis** | "Key was presented and is valid" | "Key + identity chain + governance profile + measurement evidence all verified" |
| **Performance evidence** | None; SLA is a contract clause | VNP 1,000-point score with signed multi-region observations required before connection |
| **Economic layer** | Invoice after the fact; no atomic settlement | x402 payment challenge/receipt per session; on-chain settlement target |
| **Middleware role** | Indispensable; contains all business logic | Evaporated; replaced by CAPPO policy engine + PGL + VNP |
| **Schema discovery** | OpenAPI spec (static, human-read) | GraphQL introspection + Veklom capability manifest (machine-read, real-time) |
| **Query pattern** | Fixed REST endpoints designed for UI views | Dynamic GraphQL mutations crafted by agent for exact task |
| **Audit trail** | Application logs (mutable, siloed) | Covenant Proof with PGL attestation (append-only, signed, cross-system) |
| **Safety gates** | Rate limiting only; application-layer | CAPPO continuous monitor: cost ceiling, semantic failure rate, VNP score drift |
| **Agent support** | Bolted on; agents use same endpoints as browsers | Native; agent DID is a first-class principal type |
| **Failure mode** | API down → agent fails; no structured recovery | VNP score drops → CAPPO suspends connection; agent receives structured remediation path |
| **Provider accountability** | SLA violation → dispute process | Provider bond registered; VNP evidence triggers automatic penalty calculation |

---

## Part IV — Trust Connection Technical Schema

```sql
-- Trust Connection: canonical record of a governed API relationship
CREATE TABLE trust_connections (
  -- Identity
  id                        UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  external_ref              TEXT UNIQUE,

  -- Principal chain
  agent_did                 TEXT NOT NULL,
  principal_did             TEXT NOT NULL,
  pgl_resolution_id         UUID REFERENCES pgl_resolutions(id),

  -- Target
  api_id                    UUID NOT NULL REFERENCES apis(id),
  endpoint_pattern          TEXT,

  -- Governance
  cappo_policy_id           UUID NOT NULL REFERENCES cappo_policies(id),
  cappo_policy_version      TEXT NOT NULL,
  cappo_evaluation_result   TEXT NOT NULL,
  cappo_conditions          JSONB,

  -- VNP gate snapshot (at connection time)
  vnp_score_at_connection   INTEGER,
  vnp_evidence_count        INTEGER,
  vnp_gate_result           TEXT NOT NULL,
  vnp_score_minimum_required INTEGER,
  vnp_observation_ids       UUID[],

  -- Economic
  x402_required             BOOLEAN NOT NULL DEFAULT FALSE,
  x402_challenge_id         UUID REFERENCES x402_challenges(id),
  x402_receipt_id           TEXT,
  x402_asset                TEXT,
  x402_amount               DECIMAL(18,6),
  x402_settlement_stage     TEXT NOT NULL DEFAULT 'Not Configured',
  x402_settlement_evidence  JSONB,

  -- Lifecycle state
  -- Valid: INITIALIZING | PENDING_PAYMENT | ACTIVE | SUSPENDED | TERMINATED | FAILED | REVOKED
  state                     TEXT NOT NULL DEFAULT 'INITIALIZING',
  state_reason              TEXT,
  suspension_reason         TEXT,

  -- Telemetry aggregates (updated continuously during ACTIVE)
  calls_made                INTEGER NOT NULL DEFAULT 0,
  calls_failed              INTEGER NOT NULL DEFAULT 0,
  semantic_pass_count       INTEGER NOT NULL DEFAULT 0,
  semantic_fail_count       INTEGER NOT NULL DEFAULT 0,
  cost_total_usd            DECIMAL(10,4) NOT NULL DEFAULT 0,
  cost_ceiling_usd          DECIMAL(10,4),
  latency_p50_ms            DECIMAL(10,2),
  latency_p95_ms            DECIMAL(10,2),

  -- Safety events
  safety_events             JSONB DEFAULT '[]',
  cappo_violations          INTEGER NOT NULL DEFAULT 0,
  last_safety_check_at      TIMESTAMPTZ,

  -- Proof
  covenant_proof_id         UUID REFERENCES covenant_proofs(id),
  pgl_attestation_id        TEXT,
  pgl_attestation_tx        TEXT,

  -- Phase timestamps
  discovery_at              TIMESTAMPTZ,
  identity_resolved_at      TIMESTAMPTZ,
  policy_evaluated_at       TIMESTAMPTZ,
  vnp_gate_evaluated_at     TIMESTAMPTZ,
  instantiated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  payment_confirmed_at      TIMESTAMPTZ,
  activated_at              TIMESTAMPTZ,
  last_activity_at          TIMESTAMPTZ,
  terminated_at             TIMESTAMPTZ,
  proof_generated_at        TIMESTAMPTZ,

  created_at                TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at                TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  metadata                  JSONB DEFAULT '{}'
);

CREATE INDEX idx_tc_agent_did ON trust_connections(agent_did);
CREATE INDEX idx_tc_api_id ON trust_connections(api_id);
CREATE INDEX idx_tc_state ON trust_connections(state);
CREATE INDEX idx_tc_activated_at ON trust_connections(activated_at);
CREATE INDEX idx_tc_cappo_policy ON trust_connections(cappo_policy_id);

ALTER TABLE trust_connections ENABLE ROW LEVEL SECURITY;
ALTER TABLE trust_connections FORCE ROW LEVEL SECURITY;

CREATE POLICY tc_agent_isolation ON trust_connections
  USING (agent_did = current_setting('app.agent_did', true));

CREATE POLICY tc_principal_read ON trust_connections
  FOR SELECT
  USING (principal_did = current_setting('app.principal_did', true));
```

---

## Part V — CAPPO Policy Layer: Backend Implementation Strategy

### 5.1 — Policy Table

```sql
CREATE TABLE cappo_policies (
  id                              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  version                         TEXT NOT NULL,
  api_id                          UUID NOT NULL REFERENCES apis(id),
  governing_principal_did         TEXT NOT NULL,

  clearance_required              TEXT[] NOT NULL DEFAULT '{}',
  allowed_endpoints               TEXT[] NOT NULL DEFAULT '{}',
  denied_endpoints                TEXT[] NOT NULL DEFAULT '{}',
  allowed_methods                 TEXT[] NOT NULL DEFAULT '{"GET","POST"}',

  rate_limit_per_minute           INTEGER,
  rate_limit_per_day              INTEGER,
  rate_limit_per_month            INTEGER,

  cost_ceiling_per_session        DECIMAL(10,4),
  cost_ceiling_per_day            DECIMAL(10,4),
  cost_ceiling_per_month          DECIMAL(10,4),

  data_classification_allowed     TEXT[] NOT NULL DEFAULT '{"PUBLIC"}',
  jurisdiction_allowed            TEXT[],

  vnp_score_minimum               INTEGER,
  vnp_evidence_minimum            INTEGER,
  vnp_signed_observations_required BOOLEAN DEFAULT TRUE,
  vnp_region_minimum              INTEGER DEFAULT 1,

  auto_suspend_on_cost_breach     BOOLEAN DEFAULT TRUE,
  auto_suspend_on_semantic_fail   BOOLEAN DEFAULT FALSE,
  semantic_fail_threshold         DECIMAL(4,3) DEFAULT 0.10,
  auto_resume_allowed             BOOLEAN DEFAULT FALSE,

  effective_from                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  effective_until                 TIMESTAMPTZ,
  superseded_by                   UUID REFERENCES cappo_policies(id),
  is_active                       BOOLEAN NOT NULL DEFAULT TRUE,

  created_at                      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  created_by_did                  TEXT NOT NULL
);
```

### 5.2 — The CAPPO Evaluator (Pure Function)

```python
# cappo/evaluator.py

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

class EvaluationResult(Enum):
    APPROVED = "APPROVED"
    DENIED = "DENIED"
    CONDITIONAL = "CONDITIONAL"

@dataclass
class CAPPOEvaluation:
    result: EvaluationResult
    policy_id: str
    policy_version: str
    denial_reason: Optional[str] = None
    conditions: list[str] = field(default_factory=list)
    gate_results: dict = field(default_factory=dict)

def evaluate_cappo(
    db_session,
    agent_did: str,
    api_id: str,
    endpoint: str,
    method: str,
    pgl_resolution: dict,
    vnp_score: dict,
    x402_context: dict
) -> CAPPOEvaluation:

    policy = (
        db_session.query(CAPPOPolicy)
        .filter_by(api_id=api_id, is_active=True)
        .order_by(CAPPOPolicy.effective_from.desc())
        .first()
    )

    if not policy:
        return CAPPOEvaluation(
            result=EvaluationResult.DENIED,
            policy_id="none",
            policy_version="none",
            denial_reason="NO_ACTIVE_POLICY"
        )

    gate_results = {}
    conditions = []
    denial_reason = None

    # Gate 1: Clearance
    agent_clearances = pgl_resolution.get("clearance_levels", [])
    clearance_pass = all(c in agent_clearances for c in policy.clearance_required)
    gate_results["clearance"] = clearance_pass
    if not clearance_pass:
        denial_reason = "INSUFFICIENT_CLEARANCE"

    # Gate 2: Endpoint
    endpoint_allowed = _match_patterns(endpoint, policy.allowed_endpoints)
    endpoint_denied = _match_patterns(endpoint, policy.denied_endpoints)
    gate_results["endpoint"] = endpoint_allowed and not endpoint_denied
    if endpoint_denied:
        denial_reason = "ENDPOINT_DENIED"

    # Gate 3: VNP score
    if policy.vnp_score_minimum is not None:
        score = vnp_score.get("score")
        evidence_count = vnp_score.get("evidence_count", 0)
        min_evidence = policy.vnp_evidence_minimum or 0

        if score is None or evidence_count < min_evidence:
            gate_results["vnp_score"] = False
            if denial_reason is None:
                denial_reason = "VNP_INSUFFICIENT_EVIDENCE"
        else:
            gate_results["vnp_score"] = score >= policy.vnp_score_minimum
            if not gate_results["vnp_score"] and denial_reason is None:
                denial_reason = f"VNP_SCORE_BELOW_MINIMUM_{policy.vnp_score_minimum}"

    # Gate 4: Cost ceiling feasibility
    # Gate 5: Data classification
    # Gate 6: Jurisdiction
    # ... (pattern continues for each gate)

    if denial_reason:
        return CAPPOEvaluation(
            result=EvaluationResult.DENIED,
            policy_id=str(policy.id),
            policy_version=policy.version,
            denial_reason=denial_reason,
            gate_results=gate_results
        )

    return CAPPOEvaluation(
        result=EvaluationResult.APPROVED,
        policy_id=str(policy.id),
        policy_version=policy.version,
        conditions=conditions,
        gate_results=gate_results
    )
```

### 5.3 — CAPPO Continuous Monitor

```python
# cappo/monitor.py

import asyncio

async def monitor_connection(connection_id: str, db_session, event_publisher):
    """Continuous safety monitor for an ACTIVE trust connection."""

    while True:
        connection = db_session.get(TrustConnection, connection_id)

        if connection.state not in ("ACTIVE", "SUSPENDED"):
            break

        policy = db_session.get(CAPPOPolicy, connection.cappo_policy_id)

        # Gate: Cost ceiling
        if policy.cost_ceiling_per_session:
            pct = connection.cost_total_usd / policy.cost_ceiling_per_session
            if pct >= 1.0:
                await _emit_safety_event(connection_id, "COST_CEILING_BREACH", {
                    "consumed": float(connection.cost_total_usd),
                    "ceiling": float(policy.cost_ceiling_per_session)
                }, event_publisher)
                if policy.auto_suspend_on_cost_breach:
                    await _suspend_connection(connection_id, "COST_CEILING_BREACH", db_session)
            elif pct >= 0.8:
                await _emit_safety_event(connection_id, "COST_CEILING_WARNING", {
                    "pct_consumed": pct
                }, event_publisher)

        # Gate: Semantic failure spike (rolling 10-minute window)
        recent_calls = _get_recent_calls(connection_id, minutes=10, db_session=db_session)
        if len(recent_calls) >= 5:
            fail_rate = sum(
                1 for c in recent_calls if not c.semantic_assertion_passed
            ) / len(recent_calls)
            if fail_rate > policy.semantic_fail_threshold:
                await _emit_safety_event(connection_id, "SEMANTIC_FAILURE_SPIKE", {
                    "rate": fail_rate,
                    "threshold": float(policy.semantic_fail_threshold)
                }, event_publisher)
                if policy.auto_suspend_on_semantic_fail:
                    await _suspend_connection(connection_id, "SEMANTIC_FAILURE_SPIKE", db_session)

        # Gate: VNP score drift
        current_vnp = await _get_live_vnp_score(connection.api_id)
        if current_vnp.get("score") and connection.vnp_score_minimum_required:
            if current_vnp["score"] < connection.vnp_score_minimum_required:
                await _emit_safety_event(connection_id, "VNP_SCORE_DROP", {
                    "previous": connection.vnp_score_at_connection,
                    "current": current_vnp["score"],
                    "minimum": connection.vnp_score_minimum_required
                }, event_publisher)

        await asyncio.sleep(30)
```

---

## Part VI — Connection Lifecycle State → API Trigger Mapping

```
State: INITIALIZING
  Entry:  POST /api/v1/connections {agent_did, api_id, endpoint_pattern}
  Needs:  PGL resolution + CAPPO evaluation
  → PENDING_PAYMENT   if x402_required=true AND evaluation=APPROVED
  → ACTIVE            if x402_required=false AND evaluation=APPROVED
  → FAILED            if PGL resolution fails OR evaluation=DENIED

State: PENDING_PAYMENT
  Entry:  automatic after INITIALIZING
  Action: POST /api/v1/x402/challenge (issue challenge to agent)
  → ACTIVE   trigger: POST /api/v1/x402/verify (agent submits payment proof)
  → FAILED   trigger: timeout (default 300s) or invalid payment

State: ACTIVE
  Entry:  payment verified OR no payment required
  Action: enable governed execution proxy for this connection_id
  → SUSPENDED    trigger: CAPPO monitor safety event (auto_suspend=true)
  → TERMINATED   trigger: POST /api/v1/connections/{id}/terminate
  → TERMINATED   trigger: natural expiry (cost ceiling, time limit)
  → REVOKED      trigger: POST /api/v1/connections/{id}/revoke (governance)
  → FAILED       trigger: unrecoverable provider error

State: SUSPENDED
  Entry:  CAPPO monitor safety event
  Action: block execution calls; notify agent with suspension_reason
  → ACTIVE       trigger: POST /api/v1/connections/{id}/resume (if auto_resume_allowed)
  → TERMINATED   trigger: agent terminates while suspended
  → REVOKED      trigger: governance escalation

State: TERMINATED
  Entry:  POST /api/v1/connections/{id}/terminate
  Action: generate Covenant Proof, submit to PGL for attestation
  Terminal. No further transitions.

State: FAILED
  Entry:  unrecoverable error during any phase
  Action: log failure, generate partial proof if possible
  Terminal. No further transitions.

State: REVOKED
  Entry:  governance event (policy change, principal deregistration, safety escalation)
  Action: immediate termination, full Covenant Proof with REVOKED tag
  Terminal. No further transitions.
```

---

## Part VII — The Governed SDK: Veklom's Unified Call

The Veklom Governed SDK is the Covenant in callable form. Three developer-facing methods
encapsulate all 9 phases.

```typescript
// Governed SDK interface (TypeScript)

interface TrustConnection {
  connection_id: string;
  state: ConnectionState;
  vnp_score: number | null;
  policy_version: string;
  x402_settlement_stage: string;
  activated_at: string | null;
}

interface ExecutionResult<T> {
  execution_id: string;
  data: T;
  latency: { dns_ms: number | null; tcp_ms: number | null; tls_ms: number | null; ttfb_ms: number | null; total_ms: number };
  cost_usd: number;
  cost_ceiling_remaining_usd: number;
  semantic_assertion_passed: boolean | null;
}

interface CovenantProof {
  proof_id: string;
  canonical_hash: string;
  signature: string;
  pgl_attestation_id: string | null;
}

class VeklomGovernedSDK {
  // Phase 0–5: Discovery → Identity → Policy → VNP gate → Instantiation → Payment
  async connect(credentials: AgentCredentials, api_id: string): Promise<TrustConnection>;

  // Phase 6: Governed execution with full telemetry
  async execute<T>(connection_id: string, query: string, variables?: Record<string, unknown>): Promise<ExecutionResult<T>>;

  // Phase 8: Termination + Covenant Proof generation + PGL attestation
  async terminate(connection_id: string): Promise<CovenantProof>;

  // Phase 0 only: Machine-readable capability manifest
  async introspect(api_id: string): Promise<CapabilityManifest>;
}
```

**Auto-generation pipeline:**
```
PostgreSQL (with RLS)
  → SQLAlchemy models
    → Strawberry GraphQL schema
      → schema.graphql
        → graphql-codegen CLI
          → TypeScript SDK (typed, compile-time validated)
          → Python SDK (dataclasses)
            → VeklomGovernedSDK wrapper (adds PGL/CAPPO/VNP/x402)
```

Every database schema change regenerates the typed SDK automatically.
The governed wrapper is the moat: no other GraphQL-over-database SDK includes the Covenant layer.

---

## Part VIII — Dashboard Capability Manifest

`GET /api/v1/covenant/manifest` — never hardcode status. Every badge derives from this.

```json
{
  "manifest_version": "1.0.0",
  "generated_at": "ISO8601",
  "node_id": "uuid",
  "capabilities": {
    "pgl_resolution": {
      "state": "Live | Config Incomplete | Not Yet Wired",
      "evidence_type": "real | stub | none",
      "last_successful_resolution": "ISO8601 | null"
    },
    "cappo_evaluation": {
      "state": "Live | Config Incomplete | Not Yet Wired",
      "policies_active": 0,
      "last_evaluation": "ISO8601 | null"
    },
    "vnp_score_gate": {
      "state": "Live | Insufficient Evidence | Not Yet Wired",
      "apis_with_sufficient_evidence": 0,
      "total_configured_apis": 0
    },
    "x402_settlement": {
      "state": "Not Configured | Configured | Payment Challenge Working | Receipt Persisted | Settlement Confirmed",
      "last_confirmed_settlement": "ISO8601 | null"
    },
    "covenant_proof": {
      "state": "Live | Methodology Target",
      "proofs_generated": 0,
      "pgl_attested": 0
    },
    "continuous_monitoring": {
      "state": "Live | Not Yet Wired",
      "active_monitors": 0
    }
  },
  "active_connections": 0,
  "total_connections_today": 0,
  "total_cost_settled_today_usd": 0
}
```

**Allowed state values (SEMANTIC_STEWARDSHIP.md):**
`Live` | `Connected` | `Partially Implemented` | `Demo Mode` | `Methodology Target` |
`Not Yet Wired` | `Config Incomplete` | `Disconnected` | `Auth Required` | `Insufficient Evidence`

No other values permitted in any public-facing UI.

---

## Part IX — Implementation Priority Order for Devin

### P0 — Without these, nothing is real
1. Fix `pgl_client.py` — real DID resolution or explicit error. Never return a fake UUID.
2. Fix VNP scoring — `null` + `insufficient_evidence` when evidence_count < minimum. Never default 100.
3. Create `cappo_policies` table and evaluator function (Section 5.2).

### P1 — Core lifecycle
4. Create `trust_connections` table (Section IV schema, with RLS).
5. Implement `POST /api/v1/connections` as a transactional 4-phase creation:
   PGL resolve → CAPPO evaluate → VNP gate → x402 challenge or ACTIVE.
6. Implement all state transitions with append-only audit log.
7. Implement `POST /api/v1/connections/{id}/terminate` with Covenant Proof generation.

### P2 — Evidence and telemetry
8. Add DNS/TCP/TLS/TTFB phase capture to governed execution proxy.
9. Add semantic assertion evaluation per call.
10. Wire execution telemetry to connection aggregate fields.

### P3 — Continuous safety
11. Implement CAPPO continuous monitor as async background task (Section 5.3).
12. Wire safety events to connection state machine (COST_CEILING_BREACH → SUSPENDED).

### P4 — Dashboard and SDK
13. Implement `GET /api/v1/covenant/manifest` (Section VIII).
14. Wire all frontend phase indicators to manifest — remove every hardcoded status string.
15. Generate TypeScript + Python SDK from GraphQL schema (Section VII pipeline).
16. Build Governed SDK wrapper with connect/execute/terminate interface.

---

*This document is an implementation specification. Every section describes required behavior.*
*"Should" means required. "Target" means aspirational — label it `Methodology Target` in all*
*public-facing UI until the implementation is live and evidence-backed.*
