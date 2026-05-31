import { test, expect } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'http://localhost:8088';

test.describe('Workspace & Command Center Assets @smoke', () => {
  test('Workspace SPA shell loads', async ({ request }) => {
    // The workspace index.html should always load on /workspace-next/
    const response = await request.get(`${BASE_URL}/workspace-next/`);
    expect(response.status()).toBe(200);
    const html = await response.text();
    // Verify it's loading the correct compiled bundle index-*.js
    expect(html).toMatch(/index-.*\.js/);
    expect(html).toMatch(/index-.*\.css/);
  });

  test('Command Center app loads', async ({ request }) => {
    const response = await request.get(`${BASE_URL}/command-center/`);
    // Even if it redirects or loads the SPA, it shouldn't 404
    expect([200, 302, 304]).toContain(response.status());
  });

  test('Terminal app loads', async ({ request }) => {
    const response = await request.get(`${BASE_URL}/terminal`);
    expect([200, 302, 304]).toContain(response.status());
  });
});
