import { test, expect } from '@playwright/test'
import { performance } from 'node:perf_hooks'
import { ArchitectureValidator } from '../../utils/validators'

/**
 * Measures baseline latency for critical configuration endpoints to guard
 * against regressions that would impact UX resilience.
 */
test.describe('API :: Performance Budget', () => {
  test('agent configuration endpoint responds within 800ms', async ({ request }) => {
    const start = performance.now()
    const response = await request.get('/api/v1/config/agents')
    const duration = performance.now() - start

    await ArchitectureValidator.assertCleanError(response)

    expect(
      duration,
      `Config endpoint latency ${Math.round(duration)}ms exceeded 800ms budget`
    ).toBeLessThan(800)

    expect(response.status()).toBe(200)
  })

  test('research optimize endpoint responds within 1.5s', async ({ request }) => {
    const start = performance.now()
    const response = await request.post('/api/v1/research/optimize_topic', {
      data: {
        topic: 'Performance budget probe',
        iteration: 0,
        kb_name: 'default',
      },
    })
    const duration = performance.now() - start

    const text = await ArchitectureValidator.assertCleanError(response, {
      allowEmpty: true,
    })

    expect(
      duration,
      `Research optimize latency ${Math.round(duration)}ms exceeded 1500ms budget`
    ).toBeLessThan(1500)

    expect(response.status()).toBeLessThan(600)

    if (text) {
      try {
        JSON.parse(text)
      } catch {
        expect(text.trim().length).toBeGreaterThan(0)
      }
    }
  })
})
