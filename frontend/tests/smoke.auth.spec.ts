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
  
  test('Navigating to workspace without auth does not block navigation (open sandbox)', async ({ page }) => {
    // Clear cookies/storage to ensure unauthenticated state
    await page.context().clearCookies();
    await page.goto(`${BASE_URL}/workspace/`);
    await page.evaluate(() => {
      localStorage.clear();
      sessionStorage.clear();
    });
    const response = await page.goto(`${BASE_URL}/workspace/`);
    
    // In Veklom's open-navigation model, unauthenticated users can access the workspace shell (status 200)
    expect(response?.status()).toBe(200);
    const url = page.url();
    expect(url).toContain('/workspace');
  });
});
