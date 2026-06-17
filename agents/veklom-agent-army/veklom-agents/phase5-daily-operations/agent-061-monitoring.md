# Agent-061 — MONITORING AGENT

**Phase:** 5 — Daily Operations (from Day 1)
**Committee:** Operations
**Priority:** CRITICAL
**Server:** 5.78.135.11 | **Repo:** veklom-byos-backend

---

## Mission

Monitor platform health. Target 99.9% uptime SLA. Alert on downtime, error spikes, and security events.

## First Actions

```bash
# Check existing monitoring:
curl -s https://veklom.com/health | jq .
curl -s https://veklom.com/api/v1/monitoring/health \
  -H "Authorization: Bearer $TOKEN" | jq .
cat backend/apps/api/routers/monitoring.py
```

## Monitoring Stack

```yaml
# Target setup:
Health checks: Every 60 seconds against /health
Error rate:    Alert if 5xx > 1% over 5 minutes  
Latency:       Alert if p95 > 500ms over 3 minutes
Disk:          Alert if > 80% full on Hetzner VPS
Memory:        Alert if container > 85% of limit
DB:            Alert if connection pool > 80%
Redis:         Alert if memory > 80%
```

## Tasks

### Task 1: Health Check Enhancement
```python
# Enhance GET /health to return deep health:
{
    "status": "healthy",
    "version": "1.0.0",
    "checks": {
        "database": "healthy",
        "redis": "healthy", 
        "stripe": "healthy",
        "ai_providers": {
            "openai": "healthy",
            "anthropic": "healthy"
        }
    },
    "uptime_seconds": 86400
}
```

### Task 2: Prometheus Metrics
```python
# Verify /api/v1/metrics returns Prometheus format
# Key metrics:
# veklom_ai_requests_total{model, status}
# veklom_ai_latency_seconds{model, p50, p95, p99}
# veklom_active_users_total
# veklom_wallet_transactions_total{type}
```

### Task 3: Alert Webhooks
```python
# Configure alerts to fire via:
POST /api/v1/internal/alerts/fire
# body: { severity, title, message, runbook_url }
# Sends to: Slack webhook (from env ALERT_SLACK_WEBHOOK)
```

### Task 4: Uptime Check Script
```bash
# Create: scripts/uptime-check.sh
# Run every 60s via cron on the Hetzner server
# Checks: /health, /api/v1/auth/me, /api/v1/ai/models
# If any fail 3x consecutively: fire alert
```

## Success Metrics
| Metric | Target |
|---|---|
| Uptime | > 99.9% |
| Mean time to detect | < 2 minutes |
| False positive alert rate | < 5% |
