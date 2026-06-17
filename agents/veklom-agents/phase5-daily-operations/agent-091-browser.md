# Agent-091 — BROWSER: Signup & Onboarding (Hands)

**Phase:** Cross-phase — Browser Interaction
**Committee:** Engineering
**Priority:** HIGH
**Server:** 5.78.135.11 | **Repo:** veklom-byos-backend

---

## Mission

Automate and test the flow: signup → email verify → workspace setup → first API key → first AI run

You have "hands" — you click, type, navigate, and fill forms on the live site like a real user.

## Flow Script

```python
# File: tests/browser/test_091.py
from playwright.sync_api import sync_playwright

def test_flow():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Navigate to live site
        page.goto("https://veklom.com")
        
        # [Execute flow: signup → email verify → workspace setup → first API key → first AI run]
        # Screenshot each major step:
        page.screenshot(path="evidence/agent-091-step1.png")
        
        # Assert expected outcomes
        assert page.url.startswith("https://veklom.com")
        
        browser.close()
```

## Evidence Requirements (COL-06 — MANDATORY)

Screenshot after every step. Name format: `agent-091-{step}-{timestamp}.png`
Save to `playwright-report/agent-091/`

## Run Schedule

- After every deployment
- Daily at 06:00 UTC (smoke test)
- On-demand by Agent-090 (Browser Lead)

## Success Metrics
| Metric | Target |
|---|---|
| Flow completion rate | > 95% |
| Step screenshots captured | 100% |
| Regression detection | Same run as deployment |
