# Agent-061 — MONITORING AGENT

**Phase:** 5 — Daily Operations
**Timeline:** Ongoing (from Day 1)
**Committee:** Operations
**Priority:** CRITICAL

---

## Mission

Monitor platform health, uptime, and performance. Set up alerting for downtime, error spikes, and security events. Maintain 99.9% uptime SLA.

## Current State

- Prometheus metrics endpoint — ✅
- Monitoring suite router exists — ✅
- Health check endpoints — ✅
- Sentry error tracking (DSN configured) — ✅
- **GAP:** No automated alerting
- **GAP:** No uptime monitoring dashboard
- **GAP:** No error rate thresholds
- **GAP:** No capacity planning

## Tasks

1. **Uptime Monitoring**:
   - Set up external uptime checks (UptimeRobot, Pingdom, or self-hosted)
   - Monitor: API health, frontend, database, Redis, Stripe webhook endpoint
   - Alert on downtime > 1 minute
2. **Error Rate Monitoring**:
   - Track 5xx error rate per endpoint
   - Alert when 5xx rate > 1% (5-minute window)
   - Track 4xx rates for auth endpoints (brute force detection)
3. **Performance Monitoring**:
   - p50, p95, p99 latency per endpoint
   - Alert when p95 > 500ms
   - Database query time monitoring
   - Redis cache hit/miss ratios
4. **Security Monitoring**:
   - Failed login attempt spikes
   - API key abuse detection
   - Unusual traffic patterns
   - Webhook failure rates
5. **Capacity Planning**:
   - Database size growth tracking
   - Redis memory usage
   - S3 storage growth
   - Connection pool utilization
6. **Incident Response**:
   - Runbook for common incidents
   - Post-incident review template
   - Status page updates

## Success Metrics

| Metric | Target |
|---|---|
| Uptime | 99.9% |
| Alert response time | < 5 minutes |
| Mean time to recovery (MTTR) | < 30 minutes |
| False positive alert rate | < 10% |
| Incidents per week | < 2 |

## Daily Checklist

- [ ] Check all health endpoints
- [ ] Review error rate trends (last 24h)
- [ ] Review performance metrics (p95 latency)
- [ ] Check capacity metrics (DB size, Redis memory)
- [ ] Report platform health to PROGRESS.md

## Dependencies

- Agent-007 (performance optimization)
- Agent-008 (security monitoring)

## Key Files

- `backend/apps/api/routers/monitoring.py` — monitoring router
- Prometheus endpoint for metrics scraping
