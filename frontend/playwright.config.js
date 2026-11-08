import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './tests/e2e',
  retries: 0,
  reporter: 'list',
  use: {
    baseURL: process.env.BIZORA_E2E_URL || 'http://127.0.0.1:3000',
    browserName: 'chromium',
    launchOptions: { executablePath: process.env.PLAYWRIGHT_CHROME_EXECUTABLE || '/usr/bin/google-chrome' },
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
  },
})
