# Veklom System Map — Locked Build Contract

**Status:** authoritative. Every claim is evidence-tagged. This is the full
governed-intelligence-control-plane model, reconciled against ground truth across
**all** workspace repos (not just `backend-2`).

**Evidence tags:** `CODE` (read the source), `MANUAL` (`USER_MANUAL.md`), `SURFACE`
(`API_SURFACE.md`), `STUB` (exists but placeholder), `MISSING` (referenced, not built).

---

## 0. Thesis

Veklom is **not an agent app or a marketplace.** It is a **sovereign control plane for
governed intelligent systems**: every important actor has identity, every action is
attributable, every runtime can be inspected, every meaningful signal can be acted on,
and every optimization is learned from auditable evidence. Agents are one kind of
governed asset inside a larger control plane.

The moat is the **closed governed loop**, not any single feature:

> actors are **born** (identity) → **constrained** (governance) → **executed** (runtime)
> → **observed** (telemetry/ledger) → **interpreted** (signals/forecast) → **improved**
> (learning) → **proven** (replay/evidence).

---

## 1. The Governed Loop (already real in code)

The loop is implemented as a real state machine in
`backend/services/orchestrator.py` (`RunOrchestrator` + `VeklomRunStateMachine`):

```
INTENT_CAPTURED → COMPILED → CONTEXTUALIZED → GOVERNED → (HELD / APPROVED / DENIED)
   → COMMITTED → ROUTED → EXECUTING → ATTESTED → BILLED → SEALED   (+ FAILED, ROLLED_BACK)
```

| Loop stage | What happens | Real code |
|---|---|---|
| **Identity** | `commit_run()` calls `pgl.commit_intent()` → pre-exec certificate, stored on `run.pgl_identity` | CODE `orchestrator.py:104` — PGL client is **STUB** |
| **Constraint** | `govern_run()` runs UACP v2 compile → v3 context → v4 governor → APPROVED/HELD/DENIED | CODE `orchestrator.py:79` (`uacp_v2/v3/v4`) |
| **Execution** | `route_run()` → `execute_run()`; `autonomous_worker.py` runs governed LangChain agents | CODE `orchestrator.py:123-128`, `core/services/autonomous_worker.py` |
| **Observation** | `attest_run()` calls `pgl.attest_outcome()` + stores evidence/output/outcome hashes | CODE `orchestrator.py:130` |
| **Interpretation** | insights/heartbeat + forecast service (EWMA+trend) | CODE `monitoring.py`, `services/forecast.py` |
| **Optimization** | `/autonomous/*` predictors, IronGrid routing substrate | CODE `autonomous.py`, `pyo3-irongrid-api` repo |
| **Proof** | `rollback_run()` PGL register; proof receipts (`evidence_id`/`proof_hash`/`replay`); audit HMAC chain | CODE `autonomous_worker.py`, `agents.py`, `audit` |

**The keystone gap:** the loop and its PGL hooks are real, but `pgl_client.py` returns
fake UUIDs (STUB), and the hot `/v1/exec` path may bypass the orchestrator. Making the
loop *enforced* = (a) make `pgl_client` persist to the real genome ledger, (b) route
execution through the orchestrator so **no agent executes anonymously.**

---

## 2. Architecture — inner engine + outer surfaces

### Inner engine (the conceptual center)
- **Genome (PGL)** — identity substrate: birth certificate before execution, declared
  purpose/jurisdiction/risk/tools/permissions/safety, lineage, hash-chained life ledger,
  replay/compliance export. Invariant: **no anonymous execution.**
- **Heartbeat (Insights)** — pulse + signals + forecast + Golden State + recommended
  actions. Interprets the system; not a passive dashboard.
- **Learning** — trains cost/quality/routing predictors from governed logs once sample
  thresholds are met; exposes trainable state + before/after impact. Evidence-driven.

### Outer surfaces (how humans work the engine)
Source · Build · Marketplace · Run · Prove · Workspace. Each reads as a surface of the
same engine, never a peer "module."

---

## 3. Cross-repo ground truth (where each layer ACTUALLY lives)

| Map layer | Implementation | Repo | Status |
|---|---|---|---|
| Genome / PGL | `agent.py`/`genome.py`/`lineage.py` schema + `agents.py` ledger; `pgl_client.py` (→ external `gnomledger`) | `backend-2`; UI in `agent-control-room` / `Agent-Control-need-pgl` | schema real; client STUB; UI prototype |
| Governed loop | `orchestrator.py` state machine + UACP v2/v3/v4 | `backend-2` | CODE real |
| Constraint | `mcp_gateway.py`, `jti_guard.py`, ZeroTrust, x402, Repo Risk Gate | `backend-2` + `repogate` | real |
| Execution | `autonomous_worker.py` (LangChain agents + proof receipts), UACP service | `backend-2` + `agent` (agent defs) + `uacp_-veklom-terminal` | real |
| Heartbeat | insights/monitoring + `services/forecast.py` | `backend-2` | forecast real; heartbeat partial |
| Learning | `/autonomous/*`, IronGrid, routing engine | `backend-2` + `pyo3-irongrid-api` + `hardened-lock-routing-engine` | partial |
| Proof / Replay | proof receipts, audit HMAC chain, UACP replay, compliance packets; semantic graph research | `backend-2` + `Veklom = Sovereign Runtime Infrastructure` (gnomledger + `ottomattas/neosemantics`) | real, scattered |
| Outer surfaces | github intake, GPC, pipelines, marketplace, deployments, workspace | `backend-2` + `veklom-control-plane` (`sovereign-control-node` frontend) | real |

---

## 4. Visual IA screen tree (the 9 top-level areas)

```
Overview ........ workspace pulse + system truth (active agents, milestones, what needs you)
                  └ heartbeat strip, recommended actions, "meaningful progress" feed

Genome .......... PGL inner engine
                  ├ Registry .......... agents/actors  →  /api/v1/agents, /agents/{id}
                  ├ Certificates ...... birth certs     →  birth_certificates (agents.py)
                  ├ Lineage ........... fork graph       →  lineage_edges
                  ├ Life Ledger ....... hash chain       →  /agents/evidence, LedgerEvent
                  ├ Passport / Posture  behavior band    →  (NEW) posture from ledger+violations
                  └ Replay ............ proof bundles     →  /agents/monthly-report, audit export

Source .......... ├ Connected Source ..  /auth/github/status|repos|repos/select
                  └ Repo Risk Gate ....  /repo-risk-gate/runs[/{id}/events|decision|ledger]   (repogate)

Build ........... ├ GPC plan compiler .  /gpc/intent-to-plan|plans|runs|observability/signals
                  ├ Pipelines .........  /pipelines[/{id}/graph|run] (real LangChain adapter)
                  └ Listing creation ..  /marketplace/listings (create/submit/review)

Marketplace ..... browse / list / install / datasheet   →  /marketplace/* , /listings/*

Run ............. ├ Deployments .......  /deployments CRUD, /edge/canary/*   (runtime STUB)
                  ├ Terminal Runtime ..  /v1/exec, /command-center/terminals/*  (uacp_-veklom-terminal)
                  ├ Playground ........  /playground/*, Compare-2
                  ├ Smart Routing .....  /routing/* (irongrid substrate)
                  └ Autonomous Jobs ...  /autonomous/* + autonomous_worker

Insights ........ Heartbeat: pulse · signals · forecast · Golden State · actions
                  →  /insights, /autonomous/forecast, /monitoring/*

Prove ........... audit · compliance · explainability · evidence · replay
                  →  /audit/logs|verify, /compliance/report, /evidence/create, /explainability/{id}

Workspace ....... team · keys · providers · models · billing · wallet · budgets
                  →  /workspace/*, /team/*, /auth/api-keys, /billing/*, /wallet/*
```

**Ambient-trail rule:** any surface that shows an action or output (Pipelines node,
Terminal session, Deployment, Autonomous job) MUST show a PGL identity/trail chip with
one-click access to the related ledger. The trail is never a hidden admin concern.

---

## 5. Wireframe spec — Genome page

```
┌ Genome / <Actor name>  · [Posture: Trusted ▾]  · cert_xxxx ··········· [Issue cert] ┐
├───────────────┬────────────────────────────────────────────────────────────────────┤
│ ACTOR LIST    │ IDENTITY CARD                                                        │
│ (registry)    │  declared purpose · jurisdiction · risk · model family · tools       │
│  ● Alpha      │  permissions · safety rules · runtime config                         │
│  ○ Beta       │  [View genome JSON]  [Verify chain]                                  │
│  ○ Gamma      ├────────────────────────────────────────────────────────────────────┤
│               │ LINEAGE          │ LIFE LEDGER (hash chain)     │ POSTURE            │
│               │  Alpha→Beta      │  birth · deploy · attest ··· │  band + recent      │
│               │  Alpha→Gamma     │  each row: event/hash/prev   │  violations/streak  │
│  + Register   ├──────────────────┴──────────────────────────────┴────────────────────┤
│               │ Tabs: [Events] [Evidence] [Replay] [Advanced]                         │
└───────────────┴────────────────────────────────────────────────────────────────────┘
```
- **Primary action:** Issue/renew certificate · Register actor.
- **Statuses:** Trusted / Cautioned / Restricted / Suspended (posture band).
- **Replay tab:** export compliance packet; clearly label simulated vs live.
- **Invariant banner** if any executing actor lacks a certificate: "N actors executing
  without PGL identity — block / inspect."

## 5b. Wireframe spec — Heartbeat (Insights) page

```
┌ Heartbeat ····················································· [last updated · live] ┐
│ SYSTEM PULSE   3 active agents · 1 awaiting approval · 0 criticals · inside band     │
├──────────────────────────────────────────────────────────────────────────────────┤
│ SIGNALS (memory-backed, each has a next step)                                       │
│  ✓ No governance violations in 72h        → [View]                                   │
│  ▲ Spend trending above baseline in 3 days → [Inspect forecast]                      │
│  ◷ Pipeline "Clinical RAG" stalled 27 min  → [Open run]                              │
├───────────────────────────────┬────────────────────────────────────────────────────┤
│ FORECAST (real, EWMA+trend)    │ GOLDEN STATE                                         │
│  30d spend proj · confidence   │  inside / outside learned band · confidence          │
│  method · samples_used         │  (insufficient_data shown honestly)                  │
├───────────────────────────────┴────────────────────────────────────────────────────┤
│ RECOMMENDED ACTIONS  [Retrain route predictor] [Inspect drift] [Promote route]       │
└──────────────────────────────────────────────────────────────────────────────────┘
```
- **Lead with interpretation, not charts.** Every signal is actionable or clearly informative.
- Forecast confidence + sample count always explicit (no forecast theater).
- Positive momentum shown alongside risk (milestones, streaks).

---

## 6. Genome-first implementation sequence (your map's order)

1. **Genome / keystone** — make `pgl_client` persist to the real ledger (DB-backed via
   `BirthCertificate`/`LedgerEvent`, or call `gnomledger`); enforce no-anonymous-execution
   by routing run/exec through `orchestrator`; expose a `/genome` surface; make trail chips
   ambient.
2. **Heartbeat** — redesign Insights around pulse/signals/forecast/Golden State/actions
   (forecast service already real — built this session).
3. **Learning** — expose trainable state, sample thresholds, before/after impact, Golden
   State bands; persist trained predictors (forecast model already persists).
4. **Prove** — unify replay + evidence export + compliance packet around Genome + life ledger.
5. **UI regrouping** — reorganize nav into the 9 areas once inner-engine concepts are stable.

---

## 7. Risks to avoid

- **Fragmentation:** leaving Genome/Heartbeat/Learning/Proof scattered weakens the narrative.
- **Hype:** marketing "self-learning agents" without showing what learns, at what layer, on what evidence.
- **Opaque autonomy:** any output/action without a visible identity + trail chip breaks the anti-rogue promise.
- **Forecast theater:** forecasts without confidence/sample/lineage are decorative.
- **Proof detachment:** keeping replay/compliance export as isolated admin output underuses the biggest differentiator.

## 8. Honesty discipline (already in the codebase — keep it)

Backend already returns explicit empty states with reasons, `SKILL_MISSING`, `NOT_WIRED`,
`EVIDENCE_MISSING`. Every UI surface must mirror this: `verified / simulated / placeholder /
needs trace proof`. Strength, not weakness.

---

## 9. Done this session
- Forecast heart: real EWMA+trend model (`forecast_models`), persisted `/autonomous/train`,
  new `/autonomous/forecast`, consolidated the 3 linear `*30` stubs. **Shipped + live.**

*Locked. Update whenever a STUB becomes CODE.*
