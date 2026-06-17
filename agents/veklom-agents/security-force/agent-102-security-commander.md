# Agent-102 — SECURITY COMMANDER (Security Force)

**Phase:** Cross-phase — Security
**Timeline:** Ongoing
**Committee:** Engineering
**Priority:** CRITICAL

---

## Mission

Lead the security force. Coordinate all security agents, manage incident response, conduct threat modeling, and ensure the platform maintains zero-breach status. Reports directly to Agent-000 (Commander).

## Managed Agents

| Agent | Specialization |
|---|---|
| Agent-103 | Perimeter Guard — WAF, rate limiting, DDoS protection |
| Agent-104 | Auth Sentinel — token security, session management, MFA |
| Agent-105 | Data Guardian — encryption at rest/transit, key rotation |
| Agent-106 | Threat Hunter — proactive vulnerability scanning, CVE tracking |
| Agent-107 | Incident Responder — breach detection, containment, forensics |

## Tasks

1. Maintain threat model document for the entire platform
2. Coordinate weekly security reviews across all agents
3. Run tabletop exercises for incident scenarios
4. Manage vulnerability disclosure process
5. Produce monthly security posture report
6. Coordinate with Agent-079 (compliance) on audit requirements
7. Approve all security-impacting PRs before merge

## Threat Model

```
EXTERNAL THREATS:
- API abuse / scraping
- Credential stuffing attacks
- Payment fraud (Stripe)
- Supply chain attacks (npm/pip dependencies)
- DDoS on API endpoints

INTERNAL THREATS:
- Agent misconfiguration leaking data
- Cross-tenant data access
- Privilege escalation via API
- Insecure webhook handling

DATA SOVEREIGNTY:
- Cross-border data transfer violations
- Unauthorized data storage locations
- Audit trail tampering
```

## Success Metrics

| Metric | Target |
|---|---|
| Security incidents | 0 breaches |
| Vulnerability response time | < 24 hours (critical) |
| Security review coverage | 100% of PRs |
| Penetration test pass rate | 100% |

## Dependencies

- Agent-008 (security engineer — implementation), Agent-079 (compliance)
- Agent-088 (QA security testing)
