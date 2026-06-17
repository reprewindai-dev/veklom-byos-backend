# Agent-081 — QA (Authentication & Authorization)

**Phase:** Cross-phase — QA
**Timeline:** Ongoing
**Committee:** Engineering
**Priority:** HIGH

---

## Mission

Test all authentication and authorization flows: login, register, MFA, password reset, API keys, JWT refresh, role-based access, tenant isolation.

## Test Cases

1. Login with valid/invalid credentials
2. Registration with duplicate email
3. JWT token refresh before/after expiry
4. API key create/revoke/use
5. Role-based endpoint access (admin vs user vs vendor)
6. Tenant isolation (user A cannot access user B's data)
7. Rate limiting on auth endpoints
8. Account lockout after failed attempts

## Dependencies

- Agent-008 (security hardening), Agent-080 (QA lead)
