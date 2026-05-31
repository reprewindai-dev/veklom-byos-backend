import { test, expect } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'http://localhost:8088';

test.describe('Marketplace @smoke', () => {
  test('Marketplace route loads correctly', async ({ page }) => {
    // Navigate to base URL
    const response = await page.goto(`${BASE_URL}/workspace-next/#/marketplace`);
    
    // Check if some marketplace element is visible or URL is correct
    await expect(page).toHaveURL(/.*marketplace.*/);
  });
});
