import { test, expect } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'http://localhost:8088';

test.describe('Protected Endpoints Security @smoke', () => {
  test('Command Center API rejects unauthenticated requests', async ({ request }) => {
    const response = await request.get(`${BASE_URL}/api/v1/command-center/status`);
    // Should be 401 or redirect to login (if middleware redirects on UI routes)
    // For API routes, it should return 401 Unauthorized
    expect([401, 403]).toContain(response.status());
  });

  test('Terminal Run Sample API rejects unauthenticated requests', async ({ request }) => {
    const response = await request.post(`${BASE_URL}/api/v1/terminal/run-sample`, {
      data: { command: "echo test" }
    });
    expect([401, 403]).toContain(response.status());
  });
  
  test('Navigating to workspace without auth redirects to login', async ({ page }) => {
    // Clear cookies/storage to ensure unauthenticated state
    await page.context().clearCookies();
    const response = await page.goto(`${BASE_URL}/workspace-next/`);
    
    // Depending on the frontend architecture, it might render the login component inline
    await expect(page.locator('input[type="email"], input[name="email"], #email-input')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('button:has-text("ESTABLISH SECURE ACCESS")')).toBeVisible();
  });
});
