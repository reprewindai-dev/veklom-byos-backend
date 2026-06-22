# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: smoke.spec.ts >> Veklom smoke >> @smoke landing routes render
- Location: tests/smoke.spec.ts:113:7

# Error details

```
Error: no landing JS errors on https://veklom.com/status

expect(received).toHaveLength(expected)

Expected length: 0
Received length: 1
Received array:  ["Loading the script 'https://static.cloudflareinsights.com/beacon.min.js/v833ccba57c9e4d2798f2e76cebdd09a11778172276447' violates the following Content Security Policy directive: \"script-src 'self' 'unsafe-inline' 'unsafe-eval'\". Note that 'script-src-elem' was not explicitly set, so 'script-src' is used as a fallback. The action has been blocked."]
```

# Page snapshot

```yaml
- generic [active] [ref=e1]:
  - navigation [ref=e2]:
    - generic [ref=e3]:
      - link "Veklom" [ref=e4] [cursor=pointer]:
        - /url: /
        - img "Veklom" [ref=e5]
      - generic [ref=e6]:
        - link "Home" [ref=e7] [cursor=pointer]:
          - /url: /
        - link "Workspace" [ref=e8] [cursor=pointer]:
          - /url: /workspace
        - link "Privacy" [ref=e9] [cursor=pointer]:
          - /url: /legal/privacy
        - link "Terms" [ref=e10] [cursor=pointer]:
          - /url: /legal/terms
  - main [ref=e11]:
    - generic [ref=e12]:
      - heading "System Status" [level=1] [ref=e13]
      - paragraph [ref=e14]: Real-time status of Veklom services and infrastructure.
      - generic [ref=e17]: All Systems Operational
      - generic [ref=e18]:
        - heading "Core Services" [level=2] [ref=e19]
        - generic [ref=e20]:
          - generic [ref=e21]: Website & Landing Page
          - generic [ref=e23]: ● Operational
        - generic [ref=e24]:
          - generic [ref=e25]: Workspace Application
          - generic [ref=e27]: ● Operational
        - generic [ref=e28]:
          - generic [ref=e29]: API Services
          - generic [ref=e31]: ● Operational
        - generic [ref=e32]:
          - generic [ref=e33]: Authentication
          - generic [ref=e35]: ● Operational
      - generic [ref=e36]:
        - heading "Infrastructure" [level=2] [ref=e37]
        - generic [ref=e38]:
          - generic [ref=e39]: Compute Routing
          - generic [ref=e41]: ● Operational
        - generic [ref=e42]:
          - generic [ref=e43]: Database
          - generic [ref=e45]: ● Operational
        - generic [ref=e46]:
          - generic [ref=e47]: Cache & Sessions
          - generic [ref=e49]: ● Operational
        - generic [ref=e50]:
          - generic [ref=e51]: Payment Processing (Stripe)
          - generic [ref=e53]: ● Operational
      - generic [ref=e54]:
        - heading "Add-On Services" [level=2] [ref=e55]
        - generic [ref=e56]:
          - generic [ref=e57]: Command Center
          - generic [ref=e59]: ● Operational
        - generic [ref=e60]:
          - generic [ref=e61]: IronGrid (PYO3)
          - generic [ref=e63]: ● Operational
        - generic [ref=e64]:
          - generic [ref=e65]: Quantum Terminal
          - generic [ref=e67]: ● Operational
      - generic [ref=e68]:
        - heading "Recent Incidents" [level=2] [ref=e69]
        - generic [ref=e70]:
          - generic [ref=e71]: May 25, 2026
          - generic [ref=e72]: No incidents reported
          - generic [ref=e73]: All services operating normally.
      - paragraph [ref=e74]:
        - text: This page is updated manually. For automated status checks, use the
        - link "health endpoint" [ref=e75] [cursor=pointer]:
          - /url: /api/v1/health
        - text: .
```

# Test source

```ts
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
  33  | const rolloutStatuses = new Set([502, 503, 504, 520, 521, 522, 523, 524]);
  34  |
  35  | const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));
  36  |
  37  | async function waitForResponseStatus(
  38  |   api: APIRequestContext,
  39  |   url: string,
  40  |   allowedStatuses: number[],
  41  |   label: string,
  42  |   timeoutMs = 120_000
  43  | ): Promise<APIResponse> {
  44  |   const deadline = Date.now() + timeoutMs;
  45  |   let lastStatus = 'no response';
  46  |   let lastError = '';
  47  |
  48  |   while (Date.now() < deadline) {
  49  |     try {
  50  |       const response = await api.get(url, { timeout: 15_000 });
  51  |       const status = response.status();
  52  |       lastStatus = `${status} ${response.statusText()}`;
  53  |
  54  |       if (allowedStatuses.includes(status)) {
  55  |         return response;
  56  |       }
  57  |
  58  |       if (!rolloutStatuses.has(status)) {
  59  |         break;
  60  |       }
  61  |     } catch (error) {
  62  |       lastError = error instanceof Error ? error.message : String(error);
  63  |     }
  64  |
  65  |     await sleep(2_000);
  66  |   }
  67  |
  68  |   throw new Error(`${label} did not reach ${allowedStatuses.join('/')} before timeout; last=${lastStatus}${lastError ? `; error=${lastError}` : ''}`);
  69  | }
  70  |
  71  | async function gotoDuringRollout(page: Page, url: string, label: string, timeoutMs = 120_000) {
  72  |   const deadline = Date.now() + timeoutMs;
  73  |   let lastStatus = 'no response';
  74  |   let lastError = '';
  75  |
  76  |   while (Date.now() < deadline) {
  77  |     try {
  78  |       const response = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 30_000 });
  79  |       const status = response?.status();
  80  |       lastStatus = status ? `${status} ${response?.statusText()}` : 'missing navigation response';
  81  |
  82  |       if (response?.ok()) {
  83  |         return response;
  84  |       }
  85  |
  86  |       if (status && !rolloutStatuses.has(status)) {
  87  |         break;
  88  |       }
  89  |     } catch (error) {
  90  |       lastError = error instanceof Error ? error.message : String(error);
  91  |     }
  92  |
  93  |     await sleep(2_000);
  94  |   }
  95  |
  96  |   throw new Error(`${label} did not render before timeout; last=${lastStatus}${lastError ? `; error=${lastError}` : ''}`);
  97  | }
  98  |
  99  | test.describe('Veklom smoke', () => {
  100 |   test.beforeAll(async ({ request }) => {
  101 |     await waitForResponseStatus(request, BASE, [200], 'public landing');
  102 |     await waitForResponseStatus(request, endpoints.statusDataPublic, [200], 'public status/data');
  103 |   });
  104 |
  105 |   test('@smoke health endpoints resolve', async ({ request }) => {
  106 |     const r1 = await waitForResponseStatus(request, endpoints.statusDataPublic, [200], 'public status/data');
  107 |     const json = await r1.json();
  108 |     expect(json).toBeTruthy();
  109 |
  110 |     await waitForResponseStatus(request, endpoints.plans, [200, 204], 'subscription plans');
  111 |   });
  112 |
  113 |   test('@smoke landing routes render', async ({ page }) => {
  114 |     // /status and /status.html should both 200 and not throw
  115 |     for (const url of [endpoints.statusRoute, endpoints.statusHtml]) {
  116 |       // Basic sanity: page has body and no console errors of type 'error'
  117 |       const errors: string[] = [];
  118 |       page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  119 |       await gotoDuringRollout(page, url, url);
  120 |       await expect(page.locator('body')).toBeVisible();
> 121 |       expect(errors, `no landing JS errors on ${url}`).toHaveLength(0);
      |                                                        ^ Error: no landing JS errors on https://veklom.com/status
  122 |     }
  123 |   });
  124 |
  125 |   test('@smoke auth: login/signup flow', async ({ page }) => {
  126 |     page.on('console', msg => console.log(`[Browser Console] ${msg.type()}: ${msg.text()}`));
  127 |     page.on('request', req => console.log(`[Browser Request] ${req.method()} ${req.url()}`));
  128 |     page.on('response', res => console.log(`[Browser Response] ${res.status()} ${res.url()}`));
  129 |
  130 |     // Navigate to login (redirects to /workspace/login in the SPA)
  131 |     await gotoDuringRollout(page, `${BASE}/login`, 'login route');
  132 |     await page.waitForLoadState('networkidle');
  133 |
  134 |     // The control plane is a Next App Router export, not a Vite SPA; assert the rendered auth shell.
  135 |     await expect(page.locator('main')).toBeVisible({ timeout: 15000 });
  136 |     await expect(page.getByText(/welcome back|sovereign sign-in|sign in/i).first()).toBeVisible({ timeout: 15000 });
  137 |
  138 |     // Look for any sign-up / register link or button (flexible selector)
  139 |     const signUpTrigger = page
  140 |       .getByRole('button', { name: /sign.?up|register|create.?account/i })
  141 |       .or(page.getByRole('link', { name: /sign.?up|register|create.?account/i }))
  142 |       .or(page.locator('[id*="tab-up"], [id*="tab-signup"], [data-tab="signup"]'))
  143 |       .first();
  144 |
  145 |     const signUpVisible = await signUpTrigger.isVisible().catch(() => false);
  146 |     if (signUpVisible) {
  147 |       await signUpTrigger.click();
  148 |       await page.waitForTimeout(500);
  149 |     }
  150 |
  151 |     // Try to fill an email field if present (best-effort; SPA may require different flow)
  152 |     const emailInput = page.locator('input[type="email"], input[name="email"], #vk-email').first();
  153 |     const emailVisible = await emailInput.isVisible().catch(() => false);
  154 |     if (emailVisible) {
  155 |       const testEmail = process.env.TEST_EMAIL || `smoke+signup${Date.now()}@example.com`;
  156 |       await emailInput.fill(testEmail);
  157 |       const passInput = page.locator('input[type="password"], #vk-pass').first();
  158 |       if (await passInput.isVisible().catch(() => false)) {
  159 |         await passInput.fill(process.env.TEST_PASSWORD || 'Playwright!234');
  160 |       }
  161 |       // Submit if a submit button is present
  162 |       const submitBtn = page.locator('#vk-submit, button[type="submit"]').first();
  163 |       if (await submitBtn.isVisible().catch(() => false)) {
  164 |         await submitBtn.click({ force: true });
  165 |         await page.waitForTimeout(2000);
  166 |       }
  167 |     }
  168 |
  169 |     // Final assertion: page body should still be alive
  170 |     await expect(page.locator('body')).toBeVisible();
  171 |   });
  172 |
  173 |   test('@smoke workspace basics (terminal/run present)', async ({ page }) => {
  174 |     await gotoDuringRollout(page, `${BASE}/workspace`, 'workspace route');
  175 |     await page.waitForLoadState('networkidle');
  176 |
  177 |     // The workspace route may redirect unauthenticated users into the Next auth shell.
  178 |     await expect(page.locator('body')).toBeVisible({ timeout: 15000 });
  179 |     await expect(page.locator('main, nav, [role="navigation"]').first()).toBeVisible({ timeout: 15000 });
  180 |
  181 |     // If the workspace sidebar is visible, check for key nav items.
  182 |     // If the user is unauthenticated the control plane shows a login screen — skip nav checks.
  183 |     const navVisible = await page.locator('nav, [role="navigation"]').first().isVisible().catch(() => false);
  184 |     if (navVisible) {
  185 |       const expected = [
  186 |         /terminal|console/i,
  187 |         /marketplace|apps/i,
  188 |         /pipelines?|workflow/i,
  189 |         /billing|subscription/i
  190 |       ];
  191 |       for (const pattern of expected) {
  192 |         await expect(page.getByText(pattern).first()).toBeVisible({ timeout: 10_000 });
  193 |       }
  194 |
  195 |       // Try a simple no-op job/run button if present
  196 |       const runBtn = page.getByRole('button', { name: /run|execute|start/i }).first();
  197 |       if (await runBtn.isVisible().catch(() => false)) {
  198 |         await runBtn.click();
  199 |         await page.waitForTimeout(1000);
  200 |         await expect(page.locator('body')).toBeVisible();
  201 |       }
  202 |     } else {
  203 |       // Unauthenticated: control plane loaded but shows login; that's acceptable for smoke.
  204 |       console.log('Workspace loaded in unauthenticated state; skipping nav element checks.');
  205 |       await expect(page.locator('body')).toBeVisible();
  206 |     }
  207 |   });
  208 |
  209 |   test('@smoke footer & DSA/Contact presence', async ({ page }) => {
  210 |     await gotoDuringRollout(page, BASE, 'public landing');
  211 |     await page.getByRole('contentinfo'); // footer landmark
  212 |     const footerLinks = [
  213 |       /terms|tos/i,
  214 |       /privacy/i,
  215 |       /status/i,
  216 |       /contact|dsa|legal/i
  217 |     ];
  218 |     for (const l of footerLinks) {
  219 |       await expect(page.getByRole('link', { name: l }).first()).toBeVisible();
  220 |     }
  221 |   });
```