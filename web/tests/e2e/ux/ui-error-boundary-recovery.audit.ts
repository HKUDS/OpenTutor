import { test, expect } from '@playwright/test'

const BASE_URL =
  process.env.WEB_BASE_URL || process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:3000'

/**
 * Ensures UI error boundaries recover gracefully after transient backend issues.
 */
test.describe('UX :: Error Boundary Recovery', () => {
  test('UI recovers after backend failure and subsequent navigation', async ({ page }) => {
    await page.route('**/api/v1/notebook/list', route =>
      route.fulfill({
        status: 500,
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ detail: 'Simulated Failure' }),
      })
    )

    const consoleErrors: string[] = []
    page.on('console', message => {
      if (message.type() === 'error') {
        consoleErrors.push(message.text())
      }
    })

    await page.goto(`${BASE_URL}/notebook`)

    const errorState = page.locator('[data-test=error-message]')
    await expect(errorState).toBeVisible()

    // Navigate away
    await page.goto(`${BASE_URL}/`)

    const dashboardReady = page.locator('[data-test=dashboard-ready]')
    await expect(dashboardReady).toBeVisible()

    // Navigate back — error boundary must not persist
    await page.goto(`${BASE_URL}/notebook`)

    const fallback = page.locator('[data-test=notebooks-empty]')
    await expect(fallback).toBeVisible()

    expect(consoleErrors.length).toBeGreaterThan(0)
  })
})
