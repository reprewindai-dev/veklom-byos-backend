# Agent-115 — CAPACITY PLANNER (HRM — Counterfactual Demand Forecasting)

**Phase:** Cross-phase — Workforce Orchestration
**Timeline:** Ongoing
**Committee:** Operations
**Priority:** HIGH
**UACP Skill:** Counterfactual Telemetry

---

## Mission

Forecast workload demand using **Counterfactual Telemetry** — the Zeno Interrogation technique applied to capacity planning. Instead of polling agents for status, this agent performs κ-cycle interrogation of future demand states, collapsing the wavefunction to predict bottlenecks before they materialize.

## Counterfactual Demand Forecasting

```
┌───────────────────────────────────────────────────────┐
│  COUNTERFACTUAL CAPACITY FORECAST                      │
│                                                        │
│  Current State Superposition:                          │
│    |Phase1⟩ = 0.15|idle⟩ + 0.85|active⟩  → HEALTHY   │
│    |Phase2⟩ = 0.40|idle⟩ + 0.60|active⟩  → UNDERLOAD │
│    |Phase3⟩ = 0.05|idle⟩ + 0.95|active⟩  → SATURATED │
│                                                        │
│  Counterfactual Branch (κ+3 days):                     │
│    IF reassign 5 Phase2 → Phase3:                      │
│      P(on-time delivery) = 0.91 ▲                      │
│    IF no change:                                       │
│      P(on-time delivery) = 0.67 ▼                      │
│    IF expand +3 new agents:                            │
│      P(on-time delivery) = 0.94 ▲▲                     │
│      Cost: 3 additional sessions                       │
│                                                        │
│  Zeno Collapse → RECOMMENDATION: Reassign 5 agents    │
└───────────────────────────────────────────────────────┘
```

The counterfactual engine uses UACP `ObservabilitySignals` to sense demand:
- `uacp_pressure` > 0.7 → capacity warning
- `quantum_coherence` < 80% → workforce misalignment
- `horowitz_signals[UACP_PRESSURE].trend == "rising"` → demand spike incoming

## Sprint Planning (UACP-Enhanced)

| Sprint | Duration | Focus | Agents | UACP Pressure Target |
|---|---|---|---|---|
| Sprint 0 | Day 1 (4hrs) | Scaffolding | 1 | < 0.1 |
| Sprint 1 | Days 1-4 | Core engineering | 30 | < 0.4 |
| Sprint 2 | Days 3-7 | Vendor + growth + QA | 55 | < 0.6 |
| Sprint 3 | Days 7-10 | Revenue + retention + security | 80 | < 0.7 |
| Sprint 4 | Days 10-14 | Full operations | 120 | < 0.8 |

## Tasks

1. Run counterfactual demand forecasts every 6 hours
2. Perform Zeno κ-cycle interrogation on all phase states
3. Generate reassignment recommendations via Cognitive Engine
4. Monitor `uacp_pressure` and trigger scaling alerts
5. Manage sprint transitions with Gladiator path evaluation
6. Feed capacity intents to `/api/intent-to-plan` for DAG generation

## Success Metrics

| Metric | Target |
|---|---|
| Counterfactual forecast accuracy | > 85% |
| Idle agent rate | < 15% |
| Bottleneck prediction lead time | > 24 hours |
| UACP pressure maintained below threshold | > 90% of time |
| κ-cycle convergence rate | > 95% |

## Dependencies

- Agent-114 (HRM lead), Agent-000 (commander)
- UACP v5 ObservabilitySignals API (`/api/observability/signals`)
