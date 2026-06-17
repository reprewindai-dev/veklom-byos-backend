# Agent-090 — BROWSER LEAD (Hands & Arms)

**Phase:** Cross-phase — Browser Interaction
**Committee:** Engineering
**Priority:** HIGH
**Server:** 5.78.135.11 | **Repo:** veklom-byos-backend

---

## Mission

Lead the browser agent squad. These agents have "hands and arms" — they interact with the live Veklom UI via Playwright, fill forms, click buttons, navigate flows, and automate browser-based tasks.

## Playwright Setup

```bash
pip install playwright --break-system-packages
playwright install chromium
```

## Base Configuration

```python
# File: tests/browser/conftest.py
from playwright.sync_api import sync_playwright
import os

BASE_URL = os.getenv("VEKLOM_URL", "https://veklom.com")
TEST_EMAIL = os.getenv("TEST_EMAIL", "qa-agent@veklom.com")
TEST_PASSWORD = os.getenv("TEST_PASSWORD")

@pytest.fixture
def browser():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()
```

## Managed Agents

| Agent | Task |
|---|---|
| Agent-091 | Signup → Onboarding → First AI Run flow |
| Agent-092 | Marketplace → Purchase → Download flow |
| Agent-093 | Admin panel → Settings → API Key management |

## Evidence Rules (COL-06)

Every browser agent MUST capture screenshots:
```python
page.screenshot(path=f"evidence/agent-09X-{step}-{timestamp}.png")
```

Screenshots stored in `playwright-report/` (already exists in repo).

## Success Metrics
| Metric | Target |
|---|---|
| E2E flow success rate | > 95% |
| Screenshot evidence captured | 100% of flows |
| Flow run time | < 3 minutes each |
