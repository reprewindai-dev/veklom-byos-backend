import { test, expect } from '@playwright/test';

test('hero CTA -> signup', async ({ page }) => {
  const base = process.env.BASE_URL || 'https://veklom.com';
  await page.goto(base, { waitUntil: 'domcontentloaded' });

  // Click the primary CTA that routes to /signup
  // Let's use robust CSS selectors to find buttons/links pointing to signup
  const cta = page.locator('a[href*="/signup"], button:has-text("Start"), a:has-text("Start")').first();
  await cta.waitFor({ state: 'visible', timeout: 15000 });
  await cta.click({ force: true });

  // Landed on /signup (which 302 redirects to /workspace/login)
  await page.waitForLoadState('networkidle');
  await expect(page).toHaveURL(/workspace\/login|signup/);

  // Basic backend health (fast, unauthenticated)
  const health = await page.request.get(`${base}/api/v1/health`);
  expect(health.ok()).toBeTruthy();

  // Cheap uptime status checks
  const status = await page.request.get(`${base}/status.html`);
  expect(status.ok()).toBeTruthy();
});
