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
    
    // Depending on the frontend router, it might redirect to /login
    await page.waitForURL(/.*(login|signup).*/, { timeout: 5000 }).catch(() => {});
    
    // Check if we are on login or get a 401/403
    const url = page.url();
    expect(url).toMatch(/.*(login|signup|401|unauthorized).*/i);
  });
});
