# Penalty Matrix

## Severity Codes
- CQ: Code Quality (no tests, hardcoded secrets, linting)
- SEC: Security (auth bypass, exposed keys, CORS wildcard)
- OPS: Operational (direct main push, no PROGRESS.md update)
- DS: Data Sovereignty (cross-tenant access, PII leakage)
- COL: Collaboration (no screenshots, scope violations)

## Penalty Levels
| Level | Action | Points Lost |
|---|---|---|
| 1 | Advisory warning | -5 |
| 2 | Fix within 4 hours | -10 |
| 3 | Priority demotion | -20 |
| 4 | 24-hour suspension | -30 |
| 5 | Permanent retirement | All |

## Auto LEVEL 5 (no vote needed)
- Production credentials in any commit
- Bypassing Agent-000
- Modifying GUARDRAILS.md without council
- Deleting audit logs
- 3rd LEVEL 4 suspension in 30 days

## Rank Thresholds
Recruit(0) → Operative(50) → Specialist(100) → Elite(200) → Commander(350)
