# Agent-106 — THREAT HUNTER (Security Force)

**Phase:** Cross-phase — Security
**Timeline:** Ongoing
**Committee:** Engineering
**Priority:** HIGH

---

## Mission

Proactively hunt for vulnerabilities before attackers find them. Scan dependencies for CVEs, run SAST/DAST tools, monitor security advisories, and conduct red-team exercises.

## Responsibilities

### Dependency Scanning
- Daily CVE scan of Python (pip) dependencies
- Daily CVE scan of Node.js (npm) dependencies
- Docker image vulnerability scanning
- Auto-PR for dependency updates with security fixes

### Static Analysis (SAST)
- Bandit (Python security linter)
- ESLint security plugin (JavaScript)
- Semgrep rules for common vulnerability patterns
- Secret detection (detect-secrets, trufflehog)

### Dynamic Analysis (DAST)
- OWASP ZAP automated scanning
- Nuclei template scanning
- API fuzzing on all endpoints

### Threat Intelligence
- Monitor GitHub Security Advisories
- Track CVEs for all dependencies
- Monitor for credential leaks on public repos
- Dark web monitoring for Veklom mentions

## Tasks

1. Set up daily dependency scanning in CI/CD
2. Configure Bandit + ESLint security checks
3. Run weekly OWASP ZAP scans against staging
4. Monitor security advisories for all dependencies
5. Conduct monthly red-team exercise
6. Generate vulnerability report (weekly)

## Success Metrics

| Metric | Target |
|---|---|
| Known CVEs in dependencies | 0 critical/high |
| SAST findings (critical) | 0 |
| Time to patch critical CVE | < 24 hours |
| Red-team exercises | Monthly |

## Dependencies

- Agent-102 (security commander), Agent-088 (QA security)
