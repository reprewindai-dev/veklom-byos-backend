import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  timeout: 90_000,
  expect: { timeout: 10_000 },
  testDir: 'tests',
  testIgnore: '**/playwright/**',
  retries: process.env.CI ? 2 : 0,
  reporter: [['list'], ['html', { outputFolder: 'playwright-report', open: 'never' }]],
  use: {
    baseURL: process.env.BASE_URL || 'https://veklom.com',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    ignoreHTTPSErrors: true,
    extraHTTPHeaders: {
      // Let your backend differentiate test traffic if useful
      'X-Test-Run': 'playwright-smoke'
    }
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
  // Tag filtering: run only smoke by default in CI
  grep: process.env.SMOKE_ONLY ? /@smoke/ : undefined,
  workers: process.env.CI ? 2 : undefined,
});
