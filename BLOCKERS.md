# BLOCKERS.md — Known Blockers

> Last updated: 2026-05-17  
> Status: Populated after source code copy and test run

---

## Instructions

This file is updated each time tests are run against the new repo. If a test fails, it is documented here with:

- Failing command
- Exact error
- Likely cause
- Whether it blocks selling
- Recommended fix

---

## Current Status

⚠️ **Source code copy from `reprewindai-dev/byosbackened` is pending.**

This inventory and documentation layer has been created. The next step is to copy the verified backend source files from:

```
reprewindai-dev/byosbackened @ 8241cb7
├── backend/apps/
├── backend/core/
├── backend/db/
├── backend/license/
├── backend/scripts/
├── backend/tests/
├── backend/requirements.txt
├── backend/Dockerfile
├── backend/docker-compose.yml
└── backend/alembic.ini
```

---

## Pending Test Results

Once source is copied, run:

```bash
# 1. Syntax / import check
python -c "from backend.apps.api.main import app; print('IMPORT OK')"

# 2. Health route check
pytest backend/tests/test_health.py -v

# 3. Auth tests
pytest backend/tests/test_auth.py -v

# 4. Migration check
alembic check

# 5. Full test suite
pytest backend/tests/ -v --tb=short
```

Document any failures in this file using the format below.

---

## Blocker Format

```
### BLOCKER-001: <short description>

**Failing command:**
```
<command>
```

**Exact error:**
```
<error output>
```

**Likely cause:** <explanation>

**Blocks selling:** YES / NO

**Recommended fix:** <what to do>
```

---

## No Blockers Documented Yet

No test failures documented. This file will be updated after source copy and test execution.
