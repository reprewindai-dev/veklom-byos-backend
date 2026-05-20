# Agent-100 — DASHBOARD WATCHER (Eyes)

**Phase:** Cross-phase — Visual Monitoring
**Timeline:** Ongoing
**Committee:** Operations
**Priority:** HIGH

---

## Mission

Continuously monitor KPI dashboards and alert on visual anomalies — numbers that look wrong, charts with unexpected patterns, or displays showing error states. This agent has "eyes" that watch dashboards like a human operator would.

## Monitored Dashboards

| Dashboard | Watch For |
|---|---|
| Overview KPIs | Sudden drops in users, revenue, uptime |
| Billing/Revenue | MRR anomalies, failed payment spikes |
| Monitoring/Health | Error rate spikes, latency jumps |
| Marketplace | Listing count drops, purchase failures |
| Vendor Dashboard | Vendor churn indicators, payout failures |
| Analytics | Funnel conversion drops, traffic anomalies |

## Alert Rules

```yaml
rules:
  - name: "MRR Drop Alert"
    condition: "MRR decreases > 10% day-over-day"
    severity: critical
    notify: [agent-077, agent-050]

  - name: "Error Rate Spike"
    condition: "5xx rate > 2% for 5 minutes"
    severity: critical
    notify: [agent-061, agent-073]

  - name: "User Signup Stall"
    condition: "Zero signups for 6+ hours during business hours"
    severity: warning
    notify: [agent-074, agent-053]

  - name: "Vendor Churn Signal"
    condition: "3+ vendors inactive > 7 days"
    severity: warning
    notify: [agent-031, agent-074]
```

## Tasks

1. Take dashboard screenshots every 15 minutes
2. Compare against expected patterns and thresholds
3. Alert on anomalies with screenshot evidence
4. Generate daily dashboard health report
5. Track long-term trends (weekly/monthly comparisons)

## Success Metrics

| Metric | Target |
|---|---|
| Dashboard monitoring coverage | 100% |
| Anomaly detection rate | > 90% |
| False alarm rate | < 10% |
| Alert response time | < 5 minutes |

## Dependencies

- Agent-098 (visual lead), Agent-061 (monitoring), Agent-053 (analytics)
