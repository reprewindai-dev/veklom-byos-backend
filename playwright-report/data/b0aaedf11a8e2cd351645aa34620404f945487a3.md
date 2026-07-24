# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: hero-cta.spec.ts >> hero CTA -> signup
- Location: tests\hero-cta.spec.ts:3:5

# Error details

```
Error: expect(received).toBeTruthy()

Received: false
```

# Page snapshot

```yaml
- generic [active] [ref=e1]:
  - alert [ref=e2]
  - main [ref=e3]:
    - generic [ref=e4]:
      - generic [ref=e6]:
        - img "Veklom" [ref=e7]
        - generic [ref=e8]: Control Plane
      - generic [ref=e9]:
        - heading "The sovereign AI control plane." [level=2] [ref=e10]
        - paragraph [ref=e11]: Watch every prompt routed, policed, and audited — on your perimeter, your keys, your region.
        - list [ref=e12]:
          - listitem [ref=e13]:
            - img [ref=e15]
            - generic [ref=e20]:
              - generic [ref=e21]: Smart routing
              - generic [ref=e22]: Every prompt routed across providers by policy and cost.
          - listitem [ref=e23]:
            - img [ref=e25]
            - generic [ref=e28]:
              - generic [ref=e29]: Governed by default
              - generic [ref=e30]: HIPAA, SOC2, PCI-DSS, GDPR — evidence on every call.
          - listitem [ref=e31]:
            - img [ref=e33]
            - generic [ref=e36]:
              - generic [ref=e37]: Sovereign perimeter
              - generic [ref=e38]: Your keys, your region, your audit trail. No leakage.
          - listitem [ref=e39]:
            - img [ref=e41]
            - generic [ref=e43]:
              - generic [ref=e44]: Live observability
              - generic [ref=e45]: Spend, latency, and policy interceptions in real time.
      - generic [ref=e46]: © 2026 Veklom · Sovereign AI Hub
    - generic [ref=e49]:
      - generic [ref=e50]: 14-day free trial
      - heading "Create your account" [level=1] [ref=e51]
      - paragraph [ref=e52]: Spin up a governed AI workspace in minutes. No credit card required to start.
      - generic [ref=e53]:
        - button "Sign up with GitHub" [ref=e54] [cursor=pointer]:
          - img [ref=e55]
          - text: Sign up with GitHub
        - generic [ref=e58]: or with email
        - generic [ref=e61]:
          - generic [ref=e62]:
            - text: Name
            - textbox "Ada Lovelace" [ref=e63]
          - generic [ref=e64]:
            - text: Work email
            - textbox "you@company.com" [ref=e65]
          - generic [ref=e66]:
            - text: Password
            - textbox "At least 8 characters" [ref=e67]
            - generic [ref=e68]: Minimum 8 characters
          - button "Create account" [ref=e69] [cursor=pointer]
        - paragraph [ref=e70]:
          - text: Already have an account?
          - link "Sign in" [ref=e71] [cursor=pointer]:
            - /url: /login
```

# Test source

```ts
  1  | import { test, expect } from '@playwright/test';
  2  | 
  3  | test('hero CTA -> signup', async ({ page }) => {
  4  |   const base = process.env.BASE_URL || 'https://veklom.com';
  5  |   await page.goto(base, { waitUntil: 'domcontentloaded' });
  6  | 
  7  |   // Click the primary CTA that routes to /signup
  8  |   // Let's use robust CSS selectors to find buttons/links pointing to signup
  9  |   const cta = page.locator('a[href*="/signup"], button:has-text("Start"), a:has-text("Start")').first();
  10 |   await cta.waitFor({ state: 'visible', timeout: 15000 });
  11 |   await cta.click({ force: true });
  12 | 
  13 |   // Landed on /signup (which 302 redirects to /workspace/login)
  14 |   await page.waitForLoadState('networkidle');
  15 |   await expect(page).toHaveURL(/workspace\/login|signup/);
  16 | 
  17 |   // Basic backend health (fast, unauthenticated)
  18 |   const health = await page.request.get(`${base}/api/v1/health`);
  19 |   expect(health.ok()).toBeTruthy();
  20 | 
  21 |   // Cheap uptime status checks
  22 |   const status = await page.request.get(`${base}/status.html`);
> 23 |   expect(status.ok()).toBeTruthy();
     |                       ^ Error: expect(received).toBeTruthy()
  24 | });
  25 | 
```