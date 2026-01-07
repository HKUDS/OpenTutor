import { test, expect } from '@playwright/test'

const BASE_URL =
  process.env.WEB_BASE_URL || process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:3000'

/**
 * Validates that core UX flows remain performant and resilient when upstream
 * services fail.
 */
test.describe('UX :: Resilience & Performance', () => {
  test('dashboard web vitals stay within performance budget', async ({ page }) => {
    await page.goto(`${BASE_URL}/`, { waitUntil: 'domcontentloaded' })

    const dashboardReady = page.locator('[data-test=dashboard-ready]')
    await expect(dashboardReady).toBeVisible()

    const vitals = await page.evaluate(async () => {
      const results: { lcp?: number; fid?: number; cls: number; fcp?: number } = {
        cls: 0,
      }

      const observers: PerformanceObserver[] = []

      if (typeof PerformanceObserver !== 'undefined') {
        try {
          const lcpObserver = new PerformanceObserver(entryList => {
            const entries = entryList.getEntries()
            const last = entries[entries.length - 1]
            if (last) {
              results.lcp = last.startTime
            }
          })
          lcpObserver.observe({ type: 'largest-contentful-paint', buffered: true })
          observers.push(lcpObserver)
        } catch (error) {
          // ignored: metric unavailable in this browser
        }

        try {
          const fidObserver = new PerformanceObserver(entryList => {
            const entries = entryList.getEntries()
            const first = entries[0] as PerformanceEventTiming | undefined
            if (first) {
              results.fid = first.processingStart - first.startTime
            }
          })
          fidObserver.observe({ type: 'first-input', buffered: true })
          observers.push(fidObserver)
        } catch (error) {
          // ignored
        }

        try {
          const clsObserver = new PerformanceObserver(entryList => {
            for (const entry of entryList.getEntries()) {
              const shift = entry as PerformanceEntry & {
                value?: number
                hadRecentInput?: boolean
              }
              if (!shift.hadRecentInput) {
                results.cls += shift.value ?? 0
              }
            }
          })
          clsObserver.observe({ type: 'layout-shift', buffered: true })
          observers.push(clsObserver)
        } catch (error) {
          // ignored
        }
      }

      const paints = performance.getEntriesByType('paint')
      const fcpEntry = paints.find(entry => entry.name === 'first-contentful-paint')
      if (fcpEntry) {
        results.fcp = fcpEntry.startTime
      }

      await new Promise<void>(resolve => {
        requestAnimationFrame(() => {
          observers.forEach(observer => observer.disconnect())
          resolve()
        })
      })

      return results
    })

    expect(vitals.lcp ?? Number.POSITIVE_INFINITY).toBeLessThan(2500)
    expect(vitals.fid ?? 0).toBeLessThan(100)
    expect(vitals.cls).toBeLessThan(0.1)
  })

  test('ui handles backend 500 errors without crashing', async ({ page }) => {
    await page.route('**/api/v1/notebook/list', route =>
      route.fulfill({
        status: 500,
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ detail: 'Simulated Backend Failure' }),
      })
    )

    await page.goto(`${BASE_URL}/notebook`, { waitUntil: 'domcontentloaded' })

    const errorNotice = page.locator('[data-test=error-message]')
    const alertRole = page.getByRole('alert')
    const fallback = page.locator('[data-test=notebooks-empty]')

    await expect(errorNotice.or(alertRole).or(fallback)).toBeVisible()
  })
})
