import { test, expect } from '@playwright/test'
import { ArchitectureValidator } from '../../utils/validators'

/**
 * Ensures error contracts remain stable across retries and the service degrades
 * gracefully when provided malformed inputs.
 */
test.describe('API :: Resilience', () => {
  test('malformed research request returns stable error contract across retries', async ({
    request,
  }) => {
    const attempts = 3
    const payload = {
      topic: null,
      iteration: -1,
      kb_name: '',
    }

    const responses = await Promise.all(
      Array.from({ length: attempts }, () =>
        request.post('/api/v1/research/optimize_topic', { data: payload })
      )
    )

    const statusCodes = new Set<number>()
    const errorTypes = new Set<string>()

    for (const response of responses) {
      const text = await ArchitectureValidator.assertCleanError(response)
      statusCodes.add(response.status())

      expect(response.status()).toBeGreaterThanOrEqual(400)
      expect(response.status()).toBeLessThan(500)

      let json: any
      try {
        json = JSON.parse(text)
      } catch {
        throw new Error('Error response was not valid JSON')
      }

      expect(json).toHaveProperty('detail')
      expect(typeof json.detail).toBe('string')

      expect(json).toHaveProperty('type')
      expect(typeof json.type).toBe('string')
      errorTypes.add(json.type)

      expect(json).toHaveProperty('status')
      expect(json.status).toBe(response.status())
    }

    expect(statusCodes.size).toBe(1)
    expect(errorTypes.size).toBe(1)
  })

  test('successful config fetch returns consistent payload across retries', async ({ request }) => {
    const attempts = 3
    const payloads = await Promise.all(
      Array.from({ length: attempts }, () => request.get('/api/v1/config/agents'))
    )

    const parsedConfigs = await Promise.all(
      payloads.map(async response => {
        const text = await ArchitectureValidator.assertCleanError(response)
        expect(response.status()).toBe(200)

        try {
          return JSON.parse(text) as Record<string, unknown>
        } catch {
          throw new Error('Config endpoint returned invalid JSON')
        }
      })
    )

    const [reference, ...rest] = parsedConfigs
    expect(reference).toBeDefined()

    for (const config of rest) {
      expect(config).toEqual(reference)
    }
  })
})
