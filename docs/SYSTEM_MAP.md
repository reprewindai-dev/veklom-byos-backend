# Veklom System Map — Locked Build Contract

**Status:** authoritative. Every claim below is evidence-tagged.
**Sources:** `USER_MANUAL.md`, `WIRING_CROSS_REFERENCE.md`, `API_SURFACE.md`, and direct source reads.

**Evidence tags**
- `CODE` — verified by reading the source file (line cited).
- `MANUAL` — documented in `USER_MANUAL.md` with response shape.
- `SURFACE` — listed in `API_SURFACE.md`.
- `STUB` — route/model exists but returns placeholder / does not perform the real work.
- `MISSING` — referenced somewhere but not implemented.

---

## 1. The Operating Model (one governed loop)

The product is ONE governed loop. Every surface either advances an asset along it or
governs/observes one segment.

```
Connected Source -> Repo Risk Gate -> Asset Wrapper (GPC) -> Marketplace Asset
   -> Workspace Install -> Deployment -> Terminal Runtime -> Evidence Ledger
```

Three cross-cutting layers wrap the entire loop (they touch every stage, they are not stages):

- **PGL Spine** — identity + hash-chained ledger for every moving part.
- **Insights / Heartbeat** — live posture + forecast + recommended actions.
- **Agency / Memory** — durable notifications, alarms, persistent memory.

---

## 2. Navigation IA (what the human sees)

```
OPERATIONS
  Overview      heartbeat dashboard (compact telemetry, recommended actions)
  Ship Asset    the spine (8 stages: stage-rail + canvas)
  Pipelines     graph builder
  Playground    governed inference + Compare-2
  Runtime       deployments + terminal + live metrics

GOVERNANCE
  Governance    audit, compliance, privacy, safety, locker, kill, budget
  Optimization  routing, jobs, usage, insights, savings, forecast
  Agency        notifications, alarms, persistent memory, approvals, jobs
  Workspace     team, keys, providers, models, billing, wallet
```

Nothing is deleted. Every current page becomes a tab/panel under one of these.

---

## 3. The Spine — stage by stage (with route backing)

| Stage | Object | Route backing | Evidence |
|---|---|---|---|
| Connected Source | GitHub repo / source | `/auth/github/status|repos|repos/select` | CODE (`auth.py`, matrix task 11) |
| Repo Risk Gate | Risk Run + ledger | `/repo-risk-gate/runs[/{id}/events|decision|ledger]` | router `repo_risk_gate.py` exists |
| Asset Wrapper (GPC) | Governed Plan | `/gpc/intent-to-plan|plans|runs|observability/signals` | router `gpc.py` exists |
| Marketplace Asset | Listing | `/marketplace/listings*`, `/marketplace/automation` | SURFACE |
| Workspace Install | Install | `/marketplace/installed`, `/workspace/providers|models` | CODE (matrix task 3) |
| Deployment | Deployment instance | `/deployments` CRUD, `/deployments/pause-all`, `/edge/canary/*` | CODE (model real, runtime STUB) |
| Terminal Runtime | Execution surface | `/v1/exec` (SSE+circuit breaker), `/command-center/terminals/*` | MANUAL §4 / CODE |
| Evidence Ledger | Proof | `/audit/logs`, `/audit/logs/{id}`, `/audit/verify/{id}`, `/agents/evidence` | MANUAL §11 / SURFACE / CODE |

**Deployment note:** `Deployment` table is real (`db/models/marketplace.py:72`), but creating a deployment
only inserts `status="pending"` with a synthetic `endpoint_url` — no real runtime spin-up. Persist real,
**execution STUB**.

---

## 4. The Three Hearts — current truth

### 4.1 PGL Spine
| Component | State | Evidence |
|---|---|---|
| `Agent`, `GenomeVersion`, `BirthCertificate`, `LineageEdge` schema | real | CODE (`db/models/agent.py`, `genome.py`, `lineage.py`) |
| `LedgerEvent` hash chain | real, honest | CODE (`agents.py` writes SHA-256 chained events) |
| `/agents/*` registry, runs, evidence, guardrails | real, no fabrication | CODE (`agents.py`) |
| `pgl_client.py` commit_intent / attest_outcome / resolve_genome | **STUB** (returns fake UUIDs) | CODE (`services/pgl_client.py`) |
| Ledger threaded through runs/inference/install/deploy | **MISSING** (only `/agents` writes) | CODE |

**Gap:** the ledger is universal in intent but only the agents router writes to it.

### 4.2 Insights / Forecast Heart
| Component | State | Evidence |
|---|---|---|
| `/insights`, `/insights/summary` aggregation over `ExecutionLog` | real | CODE (`monitoring.py:507`) |
| `/insights/savings/projected` | **STUB** (`savings * 30`, confidence 0.82 hardcoded) | CODE (`monitoring.py:585`) |
| `billing /cost/predict`, `/budget/forecast` | **STUB** (`daily_avg * 30`, linear) | CODE (`billing.py:726`) |
| `workspace` overview `forecast_eod` | linear (`burn_rate * 1440`) | CODE (`workspace.py:686-687`) |
| `/autonomous/cost/predict` | **real** (interpolates unit_cost/token from `ExecLog` when count>=10) | CODE (`autonomous.py:46-50`) |
| `/autonomous/train` | gates honestly, but **does not persist a model** | CODE (`autonomous.py:69-93`) |
| `/autonomous/quality/optimize`, `feature-flags` | **STUB** (hardcoded / echo) | CODE (`autonomous.py:96-122`) |

**Gap:** forecasting is scattered across 3 linear stubs. The only real data-driven path is
`/autonomous/cost/predict`. Training reports success without persisting an artifact.

### 4.3 Agency / Memory
| Component | State | Evidence |
|---|---|---|
| `monitoring.py` alerts | **STUB** (in-memory dict `_alerts`, dies on restart) | CODE (`monitoring.py:35`) |
| durable `alerts` table (manual §19) | **MISSING** (never built) | grep: no `class Alert` |
| `workspace.py` alert feed from `security_events` | real read | CODE (`workspace.py:481`) |
| conversation memory (Redis `conv:{ws}:{id}`) | real but **ephemeral** (24h TTL, 20 msgs) | MANUAL §6 |
| durable agent memory / approvals / scheduled jobs | **MISSING** | — |

**Gap:** Agency/Memory is greenfield. Needs durable `notifications`/`alarms` + `agent_memory` tables.
Conversation buffer stays as the hot 24h cache.

---

## 5. Real DB Schema backing the hearts (Manual §19, confirmed tables)

```
execution_logs    every /v1/exec call: tenant, model, provider, tokens, latency  (forecast source)
ai_audit_logs     immutable HMAC-SHA256 records                                   (evidence)
cost_predictions  predicted vs actual                                            (forecast training signal)
routing_decisions provider routing decisions + reasoning                          (routing/optimize)
budgets           budget limits + spend tracking                                  (forecast/alerts)
security_events   threat events + AI confidence                                   (agency alert feed)
agents / genome_versions / birth_certificates / lineage_edges / ledger events     (PGL spine)
```

---

## 6. Locked Build Order

1. **Forecast Heart** — consolidate the 3 linear stubs onto one forecast service built on the
   `/autonomous` path; give `/autonomous/train` a real persisted model over the `ExecutionLog`
   time series; repoint `insights/projected`, `billing` forecast, and `workspace` overview at it.
2. **Agency / Memory** — create durable `notifications`/`alarms` + `agent_memory` tables; wire
   `monitoring.py` off the in-memory dict; keep Redis conv buffer as hot cache.
3. **PGL Spine** — make `pgl_client` real (or DB-backed) and thread a ledger event into every
   governed action: runs, playground inference, marketplace install, deployment.
4. **IA / Ship Asset page** — wrap the now-real engine in the one-spine UI.

Rationale: identity-data already exists, so visibility (forecast) is the cheapest high-value win;
memory persistence unblocks agency; PGL threading is the deepest and benefits from the other two
being real first.

---

## 7. Honesty Discipline (already in the codebase — keep it)

The backend already returns explicit empty states with reasons, `SKILL_MISSING`, `NOT_WIRED`, and
`EVIDENCE_MISSING`. Every UI surface must mirror this: show `verified / simulated / placeholder /
needs trace proof` rather than over-claiming. This is a product strength, not a weakness.

---

*Locked: see git history for date. Update this file whenever a STUB becomes CODE.*
