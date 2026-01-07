import { test, expect } from '@playwright/test'
import { ArchitectureValidator } from '../../utils/validators'

/**
 * Validates that API error responses follow the documented schema and stay free
 * of internal implementation details.
 */
test.describe('API :: Error Contract Shape', () => {
  test('all 4xx/5xx errors must follow the standard error schema', async ({ request }) => {
    const response = await request.post('/api/v1/research/optimize_topic', {
      data: { topic: null },
    })

    const text = await ArchitectureValidator.assertCleanError(response)

    expect(response.status()).toBeGreaterThanOrEqual(400)
    expect(response.status()).toBeLessThan(600)

    const headers = response.headers()
    expect(headers['content-type'] ?? '').toMatch(/application\/json/)

    let json: any
    try {
      json = JSON.parse(text)
    } catch {
      throw new Error(`Error response was not valid JSON: ${text.slice(0, 200)}`)
    }

    expect(json).toHaveProperty('detail')
    expect(typeof json.detail).toBe('string')

    expect(json).toHaveProperty('type')
    expect(typeof json.type).toBe('string')

    expect(json).toHaveProperty('status')
    expect(typeof json.status).toBe('number')

    expect(json).not.toHaveProperty('traceback')
    expect(json).not.toHaveProperty('stack')
  })
})
