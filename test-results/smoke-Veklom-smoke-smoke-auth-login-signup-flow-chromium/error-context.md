# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: smoke.spec.ts >> Veklom smoke >> @smoke auth: login/signup flow
- Location: tests\smoke.spec.ts:58:7

# Error details

```
Test timeout of 90000ms exceeded.
```

```
Error: page.fill: Test timeout of 90000ms exceeded.
Call log:
  - waiting for locator('input[type="email"]')

```

# Page snapshot

```yaml
- generic [ref=e2]: "{\"detail\":\"Missing authentication credentials\"}"
```

# Test source

```ts
  1   | import { test, expect, request } from '@playwright/test';
  2   | 
  3   | /**
  4   |  * ENV you can pass:
  5   |  * BASE_URL=https://veklom.com
  6   |  * API_URL=https://api.veklom.com
  7   |  * TEST_EMAIL / TEST_PASSWORD for a real or seeded test user
  8   |  * FAILING_ENDPOINTS="GET /api/v1/bad1,POST /api/v1/bad2"
  9   |  * POSTHOG_KEY (optional, for event payload checks)
  10  |  */
  11  | 
  12  | const API = process.env.API_URL || 'https://api.veklom.com';
  13  | const BASE = process.env.BASE_URL || 'https://veklom.com';
  14  | 
  15  | const endpoints = {
  16  |   // Public status (should not crash UI):
  17  |   statusHtml: `${BASE}/status.html`,
  18  |   statusRoute: `${BASE}/status`,
  19  |   statusDataPublic: `${API}/status/data`,
  20  |   // Workspace-scoped equivalent should require auth:
  21  |   statusDataWorkspace: `${API}/api/v1/workspace/status/data`,
  22  |   // Pricing/plans endpoint used by landing:
  23  |   plans: `${API}/api/v1/subscriptions/plans`,
  24  | };
  25  | 
  26  | // Parse list of known-bad endpoints we want to assert fail deterministically
  27  | // Example: FAILING_ENDPOINTS='GET /api/v1/boom,POST /api/v1/miswired'
  28  | const failingList = (process.env.FAILING_ENDPOINTS || '')
  29  |   .split(',')
  30  |   .map(s => s.trim())
  31  |   .filter(Boolean);
  32  | 
  33  | test.describe('Veklom smoke', () => {
  34  | 
  35  |   test('@smoke health endpoints resolve', async ({ request }) => {
  36  |     const r1 = await request.get(endpoints.statusDataPublic);
  37  |     expect(r1.status(), 'public status/data must 200').toBe(200);
  38  |     const json = await r1.json();
  39  |     expect(json).toBeTruthy();
  40  | 
  41  |     const r2 = await request.get(endpoints.plans);
  42  |     expect([200, 204]).toContain(r2.status());
  43  |   });
  44  | 
  45  |   test('@smoke landing routes render', async ({ page }) => {
  46  |     // /status and /status.html should both 200 and not throw
  47  |     for (const url of [endpoints.statusRoute, endpoints.statusHtml]) {
  48  |       const resp = await page.goto(url, { waitUntil: 'domcontentloaded' });
  49  |       expect(resp?.ok(), `${url} should 200`).toBeTruthy();
  50  |       // Basic sanity: page has body and no console errors of type 'error'
  51  |       const errors: string[] = [];
  52  |       page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  53  |       await expect(page.locator('body')).toBeVisible();
  54  |       expect(errors, `no landing JS errors on ${url}`).toHaveLength(0);
  55  |     }
  56  |   });
  57  | 
  58  |   test('@smoke auth: login/signup flow', async ({ page }) => {
  59  |     // Adjust selectors to your real forms.
  60  |     await page.goto(`${BASE}/signup`);
> 61  |     await page.fill('input[type="email"]', process.env.TEST_EMAIL || 'smoke+signup@example.com');
      |                ^ Error: page.fill: Test timeout of 90000ms exceeded.
  62  |     await page.fill('input[type="password"]', process.env.TEST_PASSWORD || 'Playwright!234');
  63  |     await page.getByRole('button', { name: /sign up|create/i }).click();
  64  | 
  65  |     // TODO: replace with your post-signup landing selector
  66  |     await page.waitForLoadState('networkidle');
  67  |     // Accept either direct workspace or email verification interstitial
  68  |     const workspace = page.getByRole('heading', { name: /workspace|command center|dashboard/i });
  69  |     await expect(workspace.or(page.getByText(/verify|check your email/i))).toBeVisible();
  70  | 
  71  |     // Try login as well (idempotent if already signed up)
  72  |     await page.goto(`${BASE}/login`);
  73  |     await page.fill('input[type="email"]', process.env.TEST_EMAIL || 'smoke+signup@example.com');
  74  |     await page.fill('input[type="password"]', process.env.TEST_PASSWORD || 'Playwright!234');
  75  |     await page.getByRole('button', { name: /sign in|log in/i }).click();
  76  |     await page.waitForLoadState('networkidle');
  77  |     await expect(page.getByRole('main')).toBeVisible();
  78  |   });
  79  | 
  80  |   test('@smoke workspace basics (terminal/run present)', async ({ page }) => {
  81  |     await page.goto(`${BASE}/workspace`);
  82  |     await page.waitForLoadState('networkidle');
  83  | 
  84  |     // Check that the key apps/sections at least render
  85  |     const expected = [
  86  |       /terminal|console/i,
  87  |       /marketplace|apps/i,
  88  |       /pipelines?|workflow/i,
  89  |       /billing|subscription/i
  90  |     ];
  91  |     for (const pattern of expected) {
  92  |       await expect(page.getByText(pattern).first()).toBeVisible({ timeout: 10_000 });
  93  |     }
  94  | 
  95  |     // Try a simple no-op job/run button if present
  96  |     const runBtn = page.getByRole('button', { name: /run|execute|start/i }).first();
  97  |     if (await runBtn.isVisible().catch(() => false)) {
  98  |       await runBtn.click();
  99  |       await page.waitForTimeout(1000);
  100 |       await expect(page.locator('body')).toBeVisible();
  101 |     }
  102 |   });
  103 | 
  104 |   test('@smoke footer & DSA/Contact presence', async ({ page }) => {
  105 |     await page.goto(BASE);
  106 |     await page.getByRole('contentinfo'); // footer landmark
  107 |     const footerLinks = [
  108 |       /terms|tos/i,
  109 |       /privacy/i,
  110 |       /status/i,
  111 |       /contact|dsa|legal/i
  112 |     ];
  113 |     for (const l of footerLinks) {
  114 |       await expect(page.getByRole('link', { name: l }).first()).toBeVisible();
  115 |     }
  116 |   });
  117 | 
  118 |   test('@smoke headers: CSP/TLS/CORS sane', async ({ request }) => {
  119 |     const resp = await request.get(BASE, { ignoreHTTPSErrors: true });
  120 |     expect(resp.ok()).toBeTruthy();
  121 | 
  122 |     const csp = resp.headers()['content-security-policy'];
  123 |     expect(csp, 'CSP present').toBeTruthy();
  124 | 
  125 |     const hsts = resp.headers()['strict-transport-security'];
  126 |     expect(hsts || '', 'HSTS present').toMatch(/max-age=\d+/i);
  127 | 
  128 |     const cors = resp.headers()['access-control-allow-origin'];
  129 |     // Allow either specific origin or wildcard on API only
  130 |     expect(cors === undefined || cors === '*' || /^https?:\/\//.test(cors)).toBeTruthy();
  131 | 
  132 |     const frame = resp.headers()['x-frame-options'];
  133 |     expect((frame || '').toUpperCase()).toMatch(/SAMEORIGIN|DENY/);
  134 |   });
  135 | 
  136 |   test('@smoke PostHog events emit (if enabled)', async ({ page }) => {
  137 |     // Skip if no key configured on site or in env
  138 |     await page.route('**/capture/*', route => {
  139 |       // Let it pass; we'll inspect later
  140 |       route.continue();
  141 |     });
  142 |     const requests: { url: string; body?: string }[] = [];
  143 |     page.on('requestfinished', async req => {
  144 |       if (req.url().includes('/capture/') || req.url().includes('/e/')) {
  145 |         let body = '';
  146 |         try { body = (await req.postData()) || ''; } catch {}
  147 |         requests.push({ url: req.url(), body });
  148 |       }
  149 |     });
  150 |     await page.goto(BASE);
  151 |     await page.waitForTimeout(1500);
  152 |     expect(requests.length, 'At least one analytics event should fire').toBeGreaterThan(0);
  153 |   });
  154 | 
  155 |   test('@smoke known failing endpoints return expected failures', async ({ request }) => {
  156 |     test.skip(failingList.length === 0, 'No FAILING_ENDPOINTS provided');
  157 |     for (const item of failingList) {
  158 |       // Format: "METHOD /path"
  159 |       const [method, path] = item.split(/\s+/);
  160 |       const url = path.startsWith('http') ? path : `${API}${path}`;
  161 |       const resp = await request.fetch(url, { method: method as any });
```