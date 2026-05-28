import { test, expect } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'http://localhost:8088';

test.describe('Home hero CTA @smoke', () => {
  test('Landing page 200 and CTA navigates correctly', async ({ page }) => {
    // Navigate to base URL
    const response = await page.goto(BASE_URL);
    expect(response?.status()).toBe(200);

    // Look for login or get started link
    const cta = page.getByRole('link', { name: /Login|Get Started|Demo/i }).first();
    await expect(cta).toBeVisible();

    // Click and verify navigation
    await cta.click();
    // It should navigate to /login or /signup
    await page.waitForURL(/.*(login|signup).*/);
    await expect(page).toHaveURL(/.*(login|signup).*/);
  });
});
