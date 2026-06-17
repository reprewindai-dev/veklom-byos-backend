# Agent-090 — BROWSER LEAD (Hands & Arms)

**Phase:** Cross-phase — Browser Interaction
**Timeline:** Ongoing
**Committee:** Engineering
**Priority:** HIGH

---

## Mission

Lead the browser agent squad. These agents have "hands and arms" — they interact with UIs via Playwright/CDP, fill forms, click buttons, navigate flows, and automate browser-based tasks that require real DOM interaction.

## Capabilities

- Playwright browser automation via CDP (`http://localhost:29229`)
- Form filling, button clicking, navigation
- File uploads/downloads via browser
- Cookie/session management
- Screenshot capture for verification
- Multi-step flow execution (signup → onboarding → purchase)

## Tasks

1. Coordinate browser agents (091-093) on task assignments
2. Maintain Playwright scripts in `.agents/skills/browser/`
3. Define browser automation standards (selectors, waits, error handling)
4. Review browser test results and screenshots
5. Ensure browser scripts handle auth state persistence

## Managed Agents

| Agent | Specialization |
|---|---|
| Agent-091 | Signup & Onboarding Flows |
| Agent-092 | Marketplace & Purchase Flows |
| Agent-093 | Admin & Vendor Dashboard Flows |

## Playbook

```python
# Browser agent connection pattern
from playwright.sync_api import sync_playwright

p = sync_playwright().start()
browser = p.chromium.connect_over_cdp("http://localhost:29229")
context = browser.contexts[0]
page = context.pages[0]

# Navigate and interact
page.goto("https://veklom.com/login")
page.fill('[name="email"]', 'test@example.com')
page.fill('[name="password"]', 'password')
page.click('button[type="submit"]')
page.wait_for_url("**/overview")

# Screenshot for verification
page.screenshot(path="evidence/login-success.png")
```

## Success Metrics

| Metric | Target |
|---|---|
| Browser scripts maintained | 10+ |
| Flow automation coverage | All critical paths |
| Script reliability | > 95% pass rate |

## Dependencies

- Agent-080 (QA lead — test coordination)
- Agent-085 (frontend QA — shares test cases)
