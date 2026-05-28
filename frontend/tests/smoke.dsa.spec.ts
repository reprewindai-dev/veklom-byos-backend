import { test, expect } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'http://localhost:8088';

test.describe('EU Digital Services Act (DSA) Compliance @smoke @dsa', () => {

  test('DSA Notice page exists with visible single point of contact and complaint handling note', async ({ page }) => {
    // Attempting to hit a standard DSA compliance route (e.g., /legal/dsa or /dsa)
    // Adjust the path to match wherever the DSA notice is actually published
    const response = await page.goto(`${BASE_URL}/legal/dsa`);
    
    // Expect 200 OK
    expect(response?.status()).toBe(200);

    // Verify a single point of contact is visible (e.g., email or form link)
    // The DSA requires contact points for authorities and users
    const contactPoint = page.locator('text=/contact|email|support@|legal@/i').first();
    await expect(contactPoint).toBeVisible();

    // Verify a note about internal complaint handling exists
    const complaintNote = page.locator('text=/complaint handling|internal complaint|dispute/i').first();
    await expect(complaintNote).toBeVisible();
  });

  test('Complaint form is submittable and returns acknowledgment', async ({ request }) => {
    // Testing the backend complaint submission endpoint directly
    // This could also be an end-to-end UI test if a form exists at /complaints
    const response = await request.post(`${BASE_URL}/api/v1/complaints`, {
      data: {
        type: 'illegal_content',
        description: 'Test complaint for DSA compliance verification',
        contact_email: 'test@example.com'
      }
    });

    // Expecting 200 or 302 (if redirecting after submission)
    expect([200, 201, 302]).toContain(response.status());
    
    // If it returns JSON, verify it contains an acknowledgment
    if (response.status() === 200 || response.status() === 201) {
      const data = await response.json().catch(() => ({}));
      expect(data).toHaveProperty('status');
      // Could also check if an email acknowledgment is queued here
    }
  });

  test('Published policies and terms are accessible', async ({ request }) => {
    // DSA requires transparency, often fulfilled via terms of service and privacy policies
    const termsResponse = await request.get(`${BASE_URL}/legal/terms`);
    expect(termsResponse.status()).toBe(200);

    const privacyResponse = await request.get(`${BASE_URL}/legal/privacy`);
    expect(privacyResponse.status()).toBe(200);
    
    // Acceptable Use Policy is critical for DSA content moderation rules
    const aupResponse = await request.get(`${BASE_URL}/legal/acceptable-use`);
    expect(aupResponse.status()).toBe(200);
  });
});
