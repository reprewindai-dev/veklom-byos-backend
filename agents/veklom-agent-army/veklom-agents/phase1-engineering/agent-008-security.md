# Agent-008 — SECURITY ENGINEER

**Phase:** 1 — Complete the Core Product
**Timeline:** Days 1–4
**Committee:** Engineering
**Priority:** HIGH
**Server:** 5.78.135.11 | **Repo:** veklom-byos-backend

---

## Mission

Harden security across the platform. You are also the reviewer for all security-sensitive PRs from other Phase 1 agents.

## First Actions

```bash
cat backend/core/auth.py        # JWT config — check RS256, expiry
cat backend/core/security.py    # middleware — check CORS, rate limiting
cat backend/apps/api/main.py    # middleware stack order
# Run secret scan:
pip install detect-secrets --break-system-packages
detect-secrets scan --baseline .secrets.baseline
```

## Tasks

### Task 1: JWT Security Audit
```python
# Verify in backend/core/auth.py:
# ✓ Algorithm = RS256 (not HS256)
# ✓ Access token TTL < 3600s (1 hour)
# ✓ Refresh token TTL < 604800s (7 days)
# ✓ Token blacklist on logout (Redis)
# ✓ No user data in JWT payload beyond user_id + workspace_id
```

### Task 2: Rate Limiting Audit
```python
# Every public endpoint needs rate limiting:
# POST /auth/register → 5 req/min/IP
# POST /auth/login    → 10 req/min/IP
# POST /demo/*        → 10 req/hour/IP
# GET  /health        → unlimited (monitoring)
# Authenticated endpoints → 1000 req/hour/user
```

### Task 3: Stripe Webhook Signature Review
```python
# Review Agent-001's webhook handler:
# Must verify: stripe.Webhook.construct_event(payload, sig, secret)
# Must reject: any request missing stripe-signature header
# Must log: all webhook verification failures as security events
```

### Task 4: CORS Audit
```python
# File: backend/core/security.py
# Production CORS must ONLY allow:
ALLOWED_ORIGINS = [
    "https://veklom.com",
    "https://www.veklom.com", 
    "https://app.veklom.com",
]
# Never: origins=["*"] in production
```

### Task 5: Secrets Scan + Pre-commit Hook
```bash
# Install pre-commit hooks:
pip install pre-commit --break-system-packages
cat > .pre-commit-config.yaml << 'YAML'
repos:
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
  - repo: https://github.com/PyCQA/bandit
    rev: 1.7.5
    hooks:
      - id: bandit
        args: ["-ll", "-r", "backend/"]
YAML
pre-commit install
```

## Security Review Checklist (For Other Agents' PRs)

Before approving any PR from agents 001-007:
- [ ] No secrets in code
- [ ] All endpoints authenticated (unless explicitly public)
- [ ] Input validated via Pydantic
- [ ] No raw SQL (use ORM or parameterized queries)
- [ ] Rate limiting applied
- [ ] Errors don't leak internal info

## Success Metrics
| Metric | Target |
|---|---|
| Zero hardcoded secrets | 0 violations |
| JWT RS256 verified | Yes |
| CORS wildcard in production | 0 |
| All critical endpoints rate-limited | 100% |
