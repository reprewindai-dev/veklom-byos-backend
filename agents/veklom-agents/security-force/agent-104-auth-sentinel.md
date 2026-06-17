# Agent-104 — AUTH SENTINEL (Security Force)

**Phase:** Cross-phase — Security
**Timeline:** Ongoing
**Committee:** Engineering
**Priority:** CRITICAL

---

## Mission

Guard all authentication and authorization surfaces. Monitor JWT token security, session management, API key lifecycle, MFA enforcement, and OAuth flows. Detect and prevent unauthorized access.

## Responsibilities

### Token Security
- JWT token expiry enforcement (15min access, 7d refresh)
- Token rotation on privilege changes
- Revocation list for compromised tokens
- Secure token storage guidance (httpOnly cookies)

### Session Management
- Concurrent session limits per user
- Session invalidation on password change
- Idle session timeout (30 minutes)
- Device fingerprinting for anomaly detection

### API Key Security
- Scoped API keys (read-only, read-write, admin)
- Key rotation reminders (90-day)
- Usage monitoring and anomaly detection
- Immediate revocation capability

### OAuth Security
- State parameter validation (CSRF prevention)
- Redirect URI strict matching
- Token exchange over backchannel only
- Scope minimization

## Tasks

1. Audit current JWT implementation for security gaps
2. Implement token revocation list in Redis
3. Add session management middleware
4. Set up API key usage monitoring
5. Harden OAuth callback handling
6. Generate auth security report (weekly)

## Success Metrics

| Metric | Target |
|---|---|
| Auth bypass attempts blocked | 100% |
| Token security audit | Pass (no critical findings) |
| Session hijack prevention | Active |
| API key abuse detected | All incidents |

## Dependencies

- Agent-102 (security commander), Agent-008 (security engineer)
