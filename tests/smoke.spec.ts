import { test, expect, request } from '@playwright/test';

/**
 * ENV you can pass:
 * BASE_URL=https://veklom.com
 * API_URL=https://api.veklom.com
 * TEST_EMAIL / TEST_PASSWORD for a real or seeded test user
 * FAILING_ENDPOINTS="GET /api/v1/bad1,POST /api/v1/bad2"
 * POSTHOG_KEY (optional, for event payload checks)
 */

const API = process.env.API_URL || 'https://api.veklom.com';
const BASE = process.env.BASE_URL || 'https://veklom.com';

const endpoints = {
  // Public status (should not crash UI):
  statusHtml: `${BASE}/status.html`,
  statusRoute: `${BASE}/status`,
  statusDataPublic: `${API}/status/data`,
  // Workspace-scoped equivalent should require auth:
  statusDataWorkspace: `${API}/api/v1/workspace/status/data`,
  // Pricing/plans endpoint used by landing:
  plans: `${API}/api/v1/subscriptions/plans`,
};

// Parse list of known-bad endpoints we want to assert fail deterministically
// Example: FAILING_ENDPOINTS='GET /api/v1/boom,POST /api/v1/miswired'
const failingList = (process.env.FAILING_ENDPOINTS || '')
  .split(',')
  .map(s => s.trim())
  .filter(Boolean);

test.describe('Veklom smoke', () => {

  test('@smoke health endpoints resolve', async ({ request }) => {
    const r1 = await request.get(endpoints.statusDataPublic);
    expect(r1.status(), 'public status/data must 200').toBe(200);
    const json = await r1.json();
    expect(json).toBeTruthy();

    const r2 = await request.get(endpoints.plans);
    expect([200, 204]).toContain(r2.status());
  });

  test('@smoke landing routes render', async ({ page }) => {
    // /status and /status.html should both 200 and not throw
    for (const url of [endpoints.statusRoute, endpoints.statusHtml]) {
      const resp = await page.goto(url, { waitUntil: 'domcontentloaded' });
      expect(resp?.ok(), `${url} should 200`).toBeTruthy();
      // Basic sanity: page has body and no console errors of type 'error'
      const errors: string[] = [];
      page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
      await expect(page.locator('body')).toBeVisible();
      expect(errors, `no landing JS errors on ${url}`).toHaveLength(0);
    }
  });

  test('@smoke auth: login/signup flow', async ({ page }) => {
    // Navigate to signup (which triggers auth overlay in SPA)
    await page.goto(`${BASE}/signup`);
    
    // Switch to Sign Up tab
    const signUpTab = page.locator('#vk-tab-up');
    await signUpTab.waitFor({ state: 'visible', timeout: 15000 });
    await signUpTab.click();
    
    // Fill signup form (use deterministic unique email to avoid "User already exists" 409)
    const testEmail = process.env.TEST_EMAIL || `smoke+signup${Date.now()}@example.com`;
    await page.fill('#vk-email', testEmail);
    await page.fill('#vk-pass', process.env.TEST_PASSWORD || 'Playwright!234');
    await page.fill('#vk-name', 'Smoke Test User');
    await page.click('#vk-submit');

    // Wait for the success/redirect or workspace main view
    await page.waitForLoadState('networkidle');
    await page.goto(`${BASE}/workspace`);
    await page.waitForLoadState('networkidle');
    
    // Accept either direct workspace or auth state
    await expect(page.locator('#root')).toBeVisible();

    // Try login as well
    await page.goto(`${BASE}/login`);
    
    // Wait for email input to be visible in Sign In tab
    const emailInput = page.locator('#vk-email');
    await emailInput.waitFor({ state: 'visible', timeout: 15000 });
    await page.fill('#vk-email', testEmail);
    await page.fill('#vk-pass', process.env.TEST_PASSWORD || 'Playwright!234');
    await page.click('#vk-submit');
    await page.waitForLoadState('networkidle');
    
    // Verify overlay is dismissed and workspace loaded
    await expect(page.locator('#veklom-auth-overlay')).not.toBeVisible();
  });

  test('@smoke workspace basics (terminal/run present)', async ({ page }) => {
    await page.goto(`${BASE}/workspace`);
    await page.waitForLoadState('networkidle');

    // Check that the key apps/sections at least render
    const expected = [
      /terminal|console/i,
      /marketplace|apps/i,
      /pipelines?|workflow/i,
      /billing|subscription/i
    ];
    for (const pattern of expected) {
      await expect(page.getByText(pattern).first()).toBeVisible({ timeout: 10_000 });
    }

    // Try a simple no-op job/run button if present
    const runBtn = page.getByRole('button', { name: /run|execute|start/i }).first();
    if (await runBtn.isVisible().catch(() => false)) {
      await runBtn.click();
      await page.waitForTimeout(1000);
      await expect(page.locator('body')).toBeVisible();
    }
  });

  test('@smoke footer & DSA/Contact presence', async ({ page }) => {
    await page.goto(BASE);
    await page.getByRole('contentinfo'); // footer landmark
    const footerLinks = [
      /terms|tos/i,
      /privacy/i,
      /status/i,
      /contact|dsa|legal/i
    ];
    for (const l of footerLinks) {
      await expect(page.getByRole('link', { name: l }).first()).toBeVisible();
    }
  });

  test('@smoke headers: CSP/TLS/CORS sane', async ({ request }) => {
    const resp = await request.get(BASE, { ignoreHTTPSErrors: true });
    expect(resp.ok()).toBeTruthy();

    const csp = resp.headers()['content-security-policy'];
    expect(csp, 'CSP present').toBeTruthy();

    const hsts = resp.headers()['strict-transport-security'];
    expect(hsts || '', 'HSTS present').toMatch(/max-age=\d+/i);

    const cors = resp.headers()['access-control-allow-origin'];
    // Allow either specific origin or wildcard on API only
    expect(cors === undefined || cors === '*' || /^https?:\/\//.test(cors)).toBeTruthy();

    const frame = resp.headers()['x-frame-options'];
    expect((frame || '').toUpperCase()).toMatch(/SAMEORIGIN|DENY/);
  });

  test('@smoke PostHog events emit (if enabled)', async ({ page }) => {
    // Skip if no key configured on site or in env
    await page.route('**/capture/*', route => {
      // Let it pass; we'll inspect later
      route.continue();
    });
    const requests: { url: string; body?: string }[] = [];
    page.on('requestfinished', async req => {
      if (req.url().includes('/capture/') || req.url().includes('/e/')) {
        let body = '';
        try { body = (await req.postData()) || ''; } catch {}
        requests.push({ url: req.url(), body });
      }
    });
    await page.goto(BASE);
    await page.waitForTimeout(1500);
    if (requests.length === 0) {
      console.warn('PostHog is not enabled or not emitting events (likely REPLACE_ME_POSTHOG_KEY is active)');
      test.skip();
    } else {
      expect(requests.length, 'At least one analytics event should fire').toBeGreaterThan(0);
    }
  });

  test('@smoke known failing endpoints return expected failures', async ({ request }) => {
    test.skip(failingList.length === 0, 'No FAILING_ENDPOINTS provided');
    for (const item of failingList) {
      // Format: "METHOD /path"
      const [method, path] = item.split(/\s+/);
      const url = path.startsWith('http') ? path : `${API}${path}`;
      const resp = await request.fetch(url, { method: method as any });
      // Expect 4xx/5xx (adjust as needed)
      expect(String(resp.status())).toMatch(/^(400|401|403|404|409|422|500|502|503)$/);
    }
  });

  test('@smoke auth required for workspace-scoped status', async ({ request }) => {
    const r = await request.get(endpoints.statusDataWorkspace);
    expect([401, 403]).toContain(r.status());
  });
});
