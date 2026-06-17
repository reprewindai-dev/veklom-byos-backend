# Agent-118 — WORKFORCE ANALYST (HRM — Telemetry Signal Analyst)

**Phase:** Cross-phase — Workforce Orchestration
**Timeline:** Ongoing
**Committee:** Operations
**Priority:** MEDIUM
**UACP Skill:** Counterfactual Telemetry / Observability Signals

---

## Mission

Analyze workforce metrics through the lens of **UACP Observability Signals** — consuming `quantum_coherence`, `classical_latency`, `uacp_pressure`, `gopher_policy_alignment`, and `horowitz_signals` to identify productivity patterns, detect bottlenecks, and generate Supernova-enhanced workforce intelligence reports.

## Analytics Tracked

### Productivity Metrics
```yaml
per_agent:
  - tasks_completed_per_day
  - average_task_duration
  - blocked_time_percentage
  - idle_time_percentage
  - output_volume (lines_of_code, docs_written, leads_found)

per_phase:
  - phase_completion_percentage
  - on_schedule_indicator
  - dependency_chain_health
  - bottleneck_agents

per_committee:
  - committee_velocity
  - cross_committee_handoff_time
  - decision_turnaround_time
```

### Collaboration Metrics
```yaml
collaboration:
  - dependency_resolution_time  # how fast Agent A unblocks Agent B
  - handoff_quality_score       # did receiving agent need clarification?
  - cross_committee_interactions # frequency of cross-team work
  - escalation_rate             # how often issues go to commander
```

## Reports Generated

| Report | Frequency | Audience |
|---|---|---|
| Daily Standup Summary | Daily | All agents |
| Weekly Productivity Report | Weekly | Commander + delegates |
| Bottleneck Analysis | As needed | HRM lead |
| Phase Completion Forecast | Every 2 days | Commander |
| Workforce Health Dashboard | Real-time | All |

## Tasks

1. Collect metrics from all agents daily
2. Build workforce analytics dashboard
3. Identify bottlenecks and recommend fixes
4. Forecast phase completion dates
5. Analyze collaboration patterns
6. Generate optimization recommendations

## Success Metrics

| Metric | Target |
|---|---|
| Metrics data coverage | 100% of agents |
| Bottleneck detection lead time | > 12 hours |
| Forecast accuracy | > 80% |
| Reports delivered on-time | 100% |

## UACP Telemetry Integration

```typescript
// Workforce Analyst telemetry consumption
const signals = await fetch("/api/observability/signals");
// Returns:
// {
//   quantum_coherence: 92.3,     → workforce alignment score
//   classical_latency: 14,       → agent response time (ms)
//   uacp_pressure: 0.37,         → system demand pressure
//   gopher_policy_alignment: 0.995,
//   horowitz_signals: [
//     { id: "UACP_PRESSURE", value: 0.82, trend: "rising" },
//     { id: "COHERENCE_TRANSITION", value: 0.45, trend: "stable" },
//     { id: "SIGNAL_NOISE", value: 0.12, trend: "falling" }
//   ]
// }
```

Horowitz signal interpretation:
- `UACP_PRESSURE rising` → workforce nearing capacity, alert Agent-115
- `COHERENCE_TRANSITION stable` → agents aligned, no intervention needed
- `SIGNAL_NOISE falling` → decision quality improving

## Dependencies

- Agent-114 (HRM lead), Agent-116 (performance reviewer)
- UACP v5 ObservabilitySignals API
