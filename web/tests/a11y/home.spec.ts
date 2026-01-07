import { test, expect } from '../fixtures/axe-fixture'

test.describe('Accessibility :: Home Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/')
  })

  test('main content should not have automatically detectable accessibility issues', async ({
    page,
    makeAxeBuilder,
  }) => {
    const accessibilityScanResults = await makeAxeBuilder().analyze()

    expect(accessibilityScanResults.violations).toEqual([])
  })

  test('interactive elements should be focusable and have accessible names', async ({ page }) => {
    const interactiveElements = await page.locator('button, a[href], input, select, textarea').all()

    for (const element of interactiveElements) {
      await expect(element).toBeEnabled()
      const accessibleName = await element.evaluate(
        node => (node as any).ariaLabel || node.textContent.trim()
      )
      expect(accessibleName).not.toBe('')
    }
  })
})
