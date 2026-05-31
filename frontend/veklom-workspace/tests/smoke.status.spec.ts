import { test, expect } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'http://localhost:8088';

test.describe('Public Status Endpoints @smoke', () => {
  test('System health endpoint returns 200 and healthy JSON', async ({ request }) => {
    const response = await request.get(`${BASE_URL}/api/health`);
    expect(response.status()).toBe(200);
    const data = await response.json();
    expect(data).toHaveProperty('status');
  });

  test('Workspace status data endpoint returns 401 without auth', async ({ request }) => {
    const response = await request.get(`${BASE_URL}/api/v1/workspace-next/status/data`);
    expect([401, 403]).toContain(response.status());
  });
});
