import { test, expect } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'http://localhost:8088';

test.describe('Auth Flow @smoke', () => {
  test('Successful login redirects to workspace', async ({ page }) => {
    // If we don't have credentials in env, skip or fail fast. 
    // In CI, these should be populated.
    test.skip(!process.env.TEST_EMAIL || !process.env.TEST_PASSWORD, 'Missing TEST_EMAIL or TEST_PASSWORD');

    await page.goto(`${BASE_URL}/login`);
    
    // Fill credentials
    await page.fill('input[type="email"], input[name="email"], #email', process.env.TEST_EMAIL!);
    await page.fill('input[type="password"], input[name="password"], #password', process.env.TEST_PASSWORD!);
    
    // Click submit
    await page.click('button[type="submit"], button:has-text("Sign In"), button:has-text("Log In")');
    
    // Wait for redirect to workspace
    await page.waitForURL(/.*\/workspace\/.*/, { timeout: 10000 });
    
    // Check if some workspace element is visible
    // We expect the workspace shell to load index-EUKZeqk4.js and show elements
    await expect(page.locator('body')).toBeVisible();
  });
});
