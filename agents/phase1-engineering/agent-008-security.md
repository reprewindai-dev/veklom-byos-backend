# Agent-008 — SECURITY ENGINEER

**Phase:** 1 — Complete the Core Product
**Timeline:** Days 1–4
**Committee:** Engineering
**Priority:** HIGH

---

## Mission

Harden security across the platform: audit authentication flows, fine-tune rate limiting per endpoint, review Stripe webhook verification, audit CORS policy, and ensure zero-trust middleware is correctly configured.

## Current State

- Zero-trust middleware — ✅ exists
- Rate limiting middleware — ✅ exists (but not fine-tuned per endpoint)
- IDS/threat detection — ✅ exists
- JWT HS256 auth — ✅ works
- CORS configured — ✅ (production domains added)
- **GAP:** Rate limits not fine-tuned per auth endpoint (brute force risk)
- **GAP:** Stripe webhook signature verification needs audit
- **GAP:** API key scoping/permissions not enforced
- **GAP:** No CSP headers on frontend
- **GAP:** No security audit log summary

## Tasks

1. **Auth Endpoint Hardening**:
   - Rate limit `POST /auth/login` to 5 attempts/minute/IP
   - Rate limit `POST /auth/register` to 3 attempts/minute/IP
   - Rate limit `POST /auth/forgot-password` to 2 attempts/minute/email
   - Add account lockout after 10 failed attempts
2. **Stripe Webhook Security**:
   - Verify `stripe.Webhook.construct_event()` is used on all webhook endpoints
   - Verify webhook endpoints reject replay attacks (timestamp check)
   - Add webhook event deduplication (idempotency)
3. **API Key Permissions**:
   - Add scope field to API keys (read, write, admin)
   - Enforce scope checks on protected endpoints
   - Add key rotation mechanism
4. **CORS & CSP**:
   - Audit CORS origins list — remove wildcards
   - Add Content-Security-Policy headers to frontend
   - Add X-Frame-Options, X-Content-Type-Options headers
5. **Security Audit Report**:
   - Generate security posture report
   - Document all security middleware and their config
   - List known risks and mitigations

## Success Metrics

| Metric | Target |
|---|---|
| Auth rate limits configured | 3 endpoints |
| Webhook signature verification | 100% |
| API key scoping | Working |
| Security headers | CSP + XFO + XCTO |
| Known vulnerabilities | 0 critical |

## Daily Checklist

- [ ] Day 1: Auth endpoint rate limiting + account lockout
- [ ] Day 2: Stripe webhook security audit + fixes
- [ ] Day 3: API key permissions + CORS/CSP headers
- [ ] Day 4: Security audit report + PR

## Dependencies

- Agent-001 (Stripe Connect payment flow review)
- Agent-007 (rate limiting interacts with performance)

## Playbook

```
Repo: byosbackened
Branch: main
Read MASTER_STATE.md first
Focus: backend/apps/api/routers/auth.py + middleware stack in main.py
Audit: All webhook endpoints + CORS config
```
