import { test, expect } from '@playwright/test'
import { ArchitectureValidator } from '../utils/validators'

/**
 * Evaluates backend responses for leakage and schema stability.
 */
test.describe('Architecture :: Service Integrity', () => {
  test('agent configuration must expose stable interface without leakage', async ({ request }) => {
    const response = await request.get('/api/v1/config/agents')
    const bodyText = await ArchitectureValidator.assertCleanError(response)

    expect(response.status(), 'Config endpoint returned non-success status').toBe(200)

    const contentType = response.headers()['content-type'] || ''
    expect(contentType).toMatch(/application\/json/)

    if (!bodyText) {
      throw new Error('Config endpoint returned empty body')
    }

    let config: unknown
    try {
      config = JSON.parse(bodyText)
    } catch (error) {
      throw new Error('Config endpoint did not return valid JSON body')
    }

    expect(config).not.toBeNull()
    expect(typeof config).toBe('object')
    expect(Object.keys(config as Record<string, unknown>).length).toBeGreaterThan(0)
  })

  test('research pipeline handles unconfigured providers gracefully', async ({ request }) => {
    const response = await request.post('/api/v1/research/optimize_topic', {
      data: {
        topic: 'Automated Compliance Baseline',
        iteration: 0,
        kb_name: 'default',
      },
    })

    const text = await ArchitectureValidator.assertCleanError(response, {
      allowEmpty: true,
    })

    expect(
      response.status(),
      'Unconfigured provider should surface a client or server error'
    ).toBeGreaterThanOrEqual(400)
    expect(response.status()).toBeLessThan(600)

    const contentType = response.headers()['content-type'] || ''

    if (text && /application\/json/.test(contentType)) {
      try {
        JSON.parse(text)
      } catch {
        expect(text.trim()).toMatch(/^\{/)
      }
    }
  })
})
