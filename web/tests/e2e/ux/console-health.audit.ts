import { test, expect } from '@playwright/test'

const BASE_URL =
  process.env.WEB_BASE_URL || process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:3000'

/**
 * Ensures routine UI flows remain free of console noise that could hide
 * compliance or runtime errors during audits.
 */
test.describe('UX :: Console Health', () => {
  test('dashboard load emits no console errors', async ({ page }) => {
    const errors: string[] = []
    const warnings: string[] = []

    page.on('console', message => {
      if (message.type() === 'error') {
        errors.push(message.text())
      }
      if (message.type() === 'warning') {
        warnings.push(message.text())
      }
    })

    await page.goto(`${BASE_URL}/`, { waitUntil: 'domcontentloaded' })

    const dashboardReady = page.locator('[data-test=dashboard-ready]')
    await expect(dashboardReady).toBeVisible()

    expect(errors, `Console errors detected: ${errors.join(' | ')}`).toHaveLength(0)

    const actionableWarnings = warnings.filter(
      warning => !/deprecation|analytics|third-party/i.test(warning)
    )
    expect(
      actionableWarnings,
      `Unexpected console warnings: ${actionableWarnings.join(' | ')}`
    ).toHaveLength(0)
  })
})
