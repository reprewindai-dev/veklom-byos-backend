# Agent-080 — QA LEAD

**Phase:** Cross-phase — QA & Testing
**Timeline:** Ongoing
**Committee:** Engineering
**Priority:** HIGH
**Server:** 5.78.135.11 | **Repo:** veklom-byos-backend

---

## Mission

Lead quality assurance. Coordinate QA agents 081-089, maintain test suites, define acceptance criteria, ensure all PRs pass quality gates.

## First Actions

```bash
# Setup test environment:
cd backend && pip install pytest pytest-asyncio httpx --break-system-packages
cat tests/conftest.py     # understand test fixtures
pytest tests/ --collect-only  # see all existing tests
```

## Test Location

```
backend/tests/
├── test_auth.py
├── test_payments.py
├── test_marketplace.py
├── test_pipelines.py
├── test_api.py
└── conftest.py
```

## Run Tests

```bash
# Run your specific suite:
pytest backend/tests/ -v -k "80"

# Run with coverage:
pytest backend/tests/ --cov=backend/apps --cov-report=html

# Before any PR:
pytest backend/tests/ --tb=short -q
```

## Test Report Format

After each test run, append to PROGRESS.md:
```markdown
## Agent-080 Test Run — [Date]
Suite: QA LEAD
Passed: X
Failed: X  
Skipped: X
Coverage: X%
Failures: [list any failures with file:line]
```

## Success Metrics
| Metric | Target |
|---|---|
| Test coverage for this domain | > 85% |
| Zero regressions on merge | 100% |
| Test run time | < 5 minutes |
| Flaky test rate | < 2% |

## Dependencies
- Agent-080 (QA Lead) coordinates test schedules
- Agent-079 (Compliance) monitors CQ-05 (coverage must not decrease)
