import { test, expect } from '@playwright/test'
import { ArchitectureValidator } from '../utils/validators'

/**
 * Exercises burst traffic scenarios to ensure rate limiting responses include
 * actionable retry guidance without leaking implementation details.
 */
test.describe('API :: Rate Limiting', () => {
  test('burst requests return retry-after guidance when throttled', async ({ request }) => {
    const burstSize = 8
    const responses = await Promise.all(
      Array.from({ length: burstSize }, () => request.get('/api/v1/config/agents'))
    )

    const throttled = responses.filter(response => response.status() === 429)

    if (throttled.length === 0) {
      test.skip(true, 'Rate limiting not triggered in current environment')
      return
    }

    for (const response of throttled) {
      const text = await ArchitectureValidator.assertCleanError(response, {
        allowEmpty: true,
      })

      const headers = response.headers()
      expect(headers).toHaveProperty('retry-after')
      expect(headers['retry-after']).not.toBeUndefined()

      if (text) {
        let json: any
        try {
          json = JSON.parse(text)
        } catch {
          throw new Error('Rate limit response did not return JSON payload')
        }

        expect(json).toHaveProperty('detail')
        expect(typeof json.detail).toBe('string')
        expect(json.detail.toLowerCase()).toContain('retry')
      }
    }
  })

  test('respecting retry-after alleviates throttling', async ({ request }) => {
    const first = await request.get('/api/v1/config/agents')

    if (first.status() !== 429) {
      test.skip(true, 'Initial request not throttled; cannot verify retry-after behaviour')
      return
    }

    const headers = first.headers()
    const retryAfterSeconds = Number.parseFloat(headers['retry-after'] ?? '0')
    expect(Number.isFinite(retryAfterSeconds)).toBeTruthy()

    // Extra buffer to account for clock skew and server-side processing beyond Retry-After.
    const RETRY_BUFFER_MS = 200
    const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms))
    await sleep(Math.max(1000, Math.ceil(retryAfterSeconds * 1000)) + RETRY_BUFFER_MS)

    const second = await request.get('/api/v1/config/agents')
    await ArchitectureValidator.assertCleanError(second)

    expect(second.status()).toBeLessThan(429)
  })
})
