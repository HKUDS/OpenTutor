import { defineConfig, devices } from '@playwright/test'

const BASE_URL =
  process.env.WEB_BASE_URL || process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:3000'
// Respect local LLM resource constraints while allowing CI to scale out.
const preferSerialExecution = process.env.AUDIT_SERIAL === '1' || process.env.PW_SERIAL === '1'

export default defineConfig({
  testDir: './tests',
  fullyParallel: !preferSerialExecution,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: preferSerialExecution ? 1 : undefined,
  reporter: [['html', { open: 'never' }], ['list']],
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
  },
  use: {
    baseURL: BASE_URL,
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'ui-audit',
      testMatch: /.*\.audit\.ts$/,
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'accessibility',
      testMatch: /.*\.spec\.ts$/,
      use: { ...devices['Desktop Chrome'] },
    },
  ],
})
