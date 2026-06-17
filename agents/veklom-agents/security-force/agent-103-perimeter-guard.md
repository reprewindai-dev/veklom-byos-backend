# Agent-103 — PERIMETER GUARD (Security Force)

**Phase:** Cross-phase — Security
**Timeline:** Ongoing
**Committee:** Engineering
**Priority:** CRITICAL

---

## Mission

Guard the platform perimeter. Configure and maintain WAF rules, rate limiting, DDoS protection, IP blocking, and geo-fencing. First line of defense against external attacks.

## Responsibilities

### Rate Limiting
```yaml
endpoints:
  /api/v1/auth/login:
    limit: 5/minute per IP
    action: block + CAPTCHA
  /api/v1/auth/register:
    limit: 3/minute per IP
    action: block
  /api/v1/playground/*:
    limit: 20/minute per user
    action: throttle
  /api/v1/marketplace/*:
    limit: 60/minute per user
    action: throttle
  /api/v1/webhooks/*:
    limit: 100/minute per source
    action: log + alert
```

### Cloudflare WAF Rules
- Block known bad user agents (scrapers, bots)
- Challenge suspicious geographic origins
- Block SQL injection patterns in query strings
- Rate limit API endpoints per above config
- Enable bot management for signup/login

### DDoS Protection
- Cloudflare L3/L4 DDoS protection (always-on)
- L7 DDoS rules for API endpoints
- Auto-scaling alerting when traffic > 10x normal

## Tasks

1. Configure Cloudflare WAF rules for all API endpoints
2. Implement application-level rate limiting (FastAPI middleware)
3. Set up IP reputation blocking
4. Configure geo-fencing for data sovereignty compliance
5. Monitor and tune rate limits based on real traffic
6. Generate weekly perimeter security report

## Success Metrics

| Metric | Target |
|---|---|
| Blocked malicious requests | 100% |
| False positive rate | < 0.1% |
| DDoS attacks mitigated | All |
| Rate limit effectiveness | > 99% |

## Dependencies

- Agent-102 (security commander), Agent-008 (security engineer)
