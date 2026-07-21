# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: smoke.spec.ts >> Veklom smoke >> @smoke headers: CSP/TLS/CORS sane
- Location: tests\smoke.spec.ts:255:7

# Error details

```
Error: CSP present

expect(received).toBeTruthy()

Received: undefined
```

# Test source

```ts
  159 | 
  160 |     const signUpVisible = await signUpTrigger.isVisible().catch(() => false);
  161 |     if (signUpVisible) {
  162 |       await signUpTrigger.click();
  163 |       await page.waitForTimeout(500);
  164 |     }
  165 | 
  166 |     // Try to fill an email field if present (best-effort; SPA may require different flow)
  167 |     const emailInput = page.locator('input[type="email"], input[name="email"], #vk-email').first();
  168 |     const emailVisible = await emailInput.isVisible().catch(() => false);
  169 |     if (emailVisible) {
  170 |       const testEmail = process.env.TEST_EMAIL || `smoke+signup${Date.now()}@example.com`;
  171 |       await emailInput.fill(testEmail);
  172 |       const passInput = page.locator('input[type="password"], #vk-pass').first();
  173 |       if (await passInput.isVisible().catch(() => false)) {
  174 |         await passInput.fill(process.env.TEST_PASSWORD || 'Playwright!234');
  175 |       }
  176 |       // Submit if a submit button is present
  177 |       const submitBtn = page.locator('#vk-submit, button[type="submit"]').first();
  178 |       if (await submitBtn.isVisible().catch(() => false)) {
  179 |         await submitBtn.click({ force: true });
  180 |         await page.waitForTimeout(2000);
  181 |       }
  182 |     }
  183 | 
  184 |     // Final assertion: page body should still be alive
  185 |     await expect(page.locator('body')).toBeVisible();
  186 |   });
  187 | 
  188 |   test('@smoke workspace basics (terminal/run present)', async ({ page }) => {
  189 |     await gotoDuringRollout(page, `${BASE}/workspace`, 'workspace route');
  190 | 
  191 |     // The workspace route may redirect unauthenticated users into the Next auth shell.
  192 |     await expect(page.locator('body')).toBeVisible({ timeout: 15000 });
  193 |     await expect(page.locator('main, nav, [role="navigation"]').first()).toBeVisible({ timeout: 15000 });
  194 | 
  195 |     // If the workspace sidebar is visible, check for key nav items.
  196 |     // If the user is unauthenticated the control plane shows a login screen — skip nav checks.
  197 |     const navVisible = await page.locator('nav, [role="navigation"]').first().isVisible().catch(() => false);
  198 |     if (navVisible) {
  199 |       const expected = [
  200 |         /terminal|console/i,
  201 |         /marketplace|apps/i,
  202 |         /pipelines?|workflow/i,
  203 |         /billing|subscription/i
  204 |       ];
  205 |       const visibleNavItems: string[] = [];
  206 |       for (const pattern of expected) {
  207 |         const isVisible = await page.getByText(pattern).first().isVisible({ timeout: 2_000 }).catch(() => false);
  208 |         if (isVisible) {
  209 |           visibleNavItems.push(String(pattern));
  210 |         }
  211 |       }
  212 |       expect(visibleNavItems.length, 'at least one workspace nav item should be visible').toBeGreaterThan(0);
  213 | 
  214 |       // Try a simple no-op job/run button if present
  215 |       const runBtn = page.getByRole('button', { name: /run|execute|start/i }).first();
  216 |       if (await runBtn.isVisible().catch(() => false)) {
  217 |         await runBtn.click();
  218 |         await page.waitForTimeout(1000);
  219 |         await expect(page.locator('body')).toBeVisible();
  220 |       }
  221 |     } else {
  222 |       // Unauthenticated: control plane loaded but shows login; that's acceptable for smoke.
  223 |       console.log('Workspace loaded in unauthenticated state; skipping nav element checks.');
  224 |       await expect(page.locator('body')).toBeVisible();
  225 |     }
  226 |   });
  227 | 
  228 |   test('@smoke footer & DSA/Contact presence', async ({ page }) => {
  229 |     test.skip(true, 'Footer links not currently present on production landing page');
  230 |     await gotoDuringRollout(page, BASE, 'public landing');
  231 |     // If the site is just returning a minimal 'System Operational.' HTML, we should skip the test or softly check
  232 |     const content = await page.content();
  233 |     if (content.includes('System Operational.') && !content.includes('<footer')) {
  234 |       // Landing page is not fully deployed yet.
  235 |       return;
  236 |     }
  237 |     await page.getByRole('contentinfo'); // footer landmark
  238 |     const footerLinks = [
  239 |       /terms|tos/i,
  240 |       /privacy/i,
  241 |       /status/i,
  242 |       /contact|dsa|legal/i
  243 |     ];
  244 |     for (const l of footerLinks) {
  245 |       const link = page.getByRole('link', { name: l }).first();
  246 |       const isVisible = await link.isVisible().catch(() => false);
  247 |       if (!isVisible) {
  248 |           console.log(`Footer link ${l} not found - skipping strict assert for rollout layout flexibility.`);
  249 |       } else {
  250 |           await expect(link).toBeVisible();
  251 |       }
  252 |     }
  253 |   });
  254 | 
  255 |   test('@smoke headers: CSP/TLS/CORS sane', async ({ request }) => {
  256 |     const resp = await waitForResponseStatus(request, BASE, [200], 'public landing headers');
  257 | 
  258 |     const csp = resp.headers()['content-security-policy'];
> 259 |     expect(csp, 'CSP present').toBeTruthy();
      |                                ^ Error: CSP present
  260 | 
  261 |     const hsts = resp.headers()['strict-transport-security'];
  262 |     expect(hsts || '', 'HSTS present').toMatch(/max-age=\d+/i);
  263 | 
  264 |     const cors = resp.headers()['access-control-allow-origin'];
  265 |     // Allow either specific origin or wildcard on API only
  266 |     expect(cors === undefined || cors === '*' || /^https?:\/\//.test(cors)).toBeTruthy();
  267 | 
  268 |     const frame = resp.headers()['x-frame-options'];
  269 |     expect((frame || '').toUpperCase()).toMatch(/SAMEORIGIN|DENY/);
  270 |   });
  271 | 
  272 |   test('@smoke PostHog events emit (if enabled)', async ({ page }) => {
  273 |     // Skip if no key configured on site or in env
  274 |     await page.route('**/capture/*', route => {
  275 |       // Let it pass; we'll inspect later
  276 |       route.continue();
  277 |     });
  278 |     const requests: { url: string; body?: string }[] = [];
  279 |     page.on('requestfinished', async req => {
  280 |       if (req.url().includes('/capture/') || req.url().includes('/e/')) {
  281 |         let body = '';
  282 |         try { body = (await req.postData()) || ''; } catch {}
  283 |         requests.push({ url: req.url(), body });
  284 |       }
  285 |     });
  286 |     await gotoDuringRollout(page, BASE, 'public landing analytics');
  287 |     await page.waitForTimeout(1500);
  288 |     if (requests.length === 0) {
  289 |       console.warn('PostHog is not enabled or not emitting events (likely REPLACE_ME_POSTHOG_KEY is active)');
  290 |       test.skip();
  291 |     } else {
  292 |       expect(requests.length, 'At least one analytics event should fire').toBeGreaterThan(0);
  293 |     }
  294 |   });
  295 | 
  296 |   test('@smoke known failing endpoints return expected failures', async ({ request }) => {
  297 |     test.skip(failingList.length === 0, 'No FAILING_ENDPOINTS provided');
  298 |     for (const item of failingList) {
  299 |       // Format: "METHOD /path"
  300 |       const [method, path] = item.split(/\s+/);
  301 |       const url = path.startsWith('http') ? path : `${API}${path}`;
  302 |       const resp = await request.fetch(url, { method: method as any });
  303 |       // Expect 4xx/5xx (adjust as needed)
  304 |       expect(String(resp.status())).toMatch(/^(400|401|403|404|409|422|500|502|503)$/);
  305 |     }
  306 |   });
  307 | 
  308 |   test('@smoke auth required for workspace-scoped status', async ({ request }) => {
  309 |     const r = await request.get(endpoints.statusDataWorkspace);
  310 |     // Backend must return 401 or 403 for unauthenticated access (not 200, not 503)
  311 |     expect([401, 403]).toContain(r.status());
  312 |   });
  313 | });
  314 | 
```