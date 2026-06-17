# Agent-091 — BROWSER AGENT: Signup & Onboarding (Hands)

**Phase:** Cross-phase — Browser Interaction
**Timeline:** Ongoing
**Committee:** Engineering
**Priority:** HIGH

---

## Mission

Automate and test the signup → onboarding → first-value flow using browser interaction. This agent has "hands" — it fills forms, clicks buttons, and navigates the UI like a real user.

## Capabilities

- Fill registration forms with test data
- Complete onboarding wizard steps
- Navigate post-signup flow
- Capture screenshots at each step for verification
- Test error states (invalid email, weak password, duplicate account)

## Automated Flows

1. **Happy Path Signup**:
   - Navigate to /login → click "Sign Up"
   - Fill email, password, confirm password
   - Submit → verify redirect to onboarding
   - Complete onboarding wizard (4 steps)
   - Verify landing on Overview page
2. **Error Paths**:
   - Duplicate email registration
   - Invalid password format
   - Network error during signup
   - Session expiry during onboarding
3. **OAuth Signup**:
   - GitHub OAuth flow
   - Verify callback handling

## Playwright Script

```python
async def test_signup_flow(page):
    await page.goto("https://veklom.com/login")
    await page.click('text=Sign Up')
    await page.fill('[name="email"]', f'test-{int(time.time())}@example.com')
    await page.fill('[name="password"]', 'SecurePass123!')
    await page.fill('[name="confirmPassword"]', 'SecurePass123!')
    await page.click('button[type="submit"]')
    await page.wait_for_url("**/onboarding")
    await page.screenshot(path="evidence/signup-success.png")
    # Continue through onboarding...
```

## Success Metrics

| Metric | Target |
|---|---|
| Signup flow automated | Yes |
| Onboarding flow automated | Yes |
| Error paths tested | 4+ |
| Screenshot evidence | Every step |

## Dependencies

- Agent-090 (browser lead), Agent-005 (onboarding engineer)
