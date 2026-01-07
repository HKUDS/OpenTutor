import { test, expect } from '@playwright/test'
import { ArchitectureValidator } from '../../utils/validators'

/**
 * Ensures the agent configuration endpoint maintains a stable response schema.
 */
test.describe('API :: Success Contract Stability', () => {
  test('agent config endpoint exposes stable, typed structure', async ({ request }) => {
    const response = await request.get('/api/v1/config/agents')
    const text = await ArchitectureValidator.assertCleanError(response)

    expect(response.status(), 'Agent config endpoint returned non-200 status').toBe(200)

    const headers = response.headers()
    expect(headers['content-type'] ?? '').toMatch(/application\/json/)

    let json: unknown
    try {
      json = JSON.parse(text)
    } catch {
      throw new Error('Agent config endpoint returned non-JSON payload')
    }

    expect(json && typeof json === 'object').toBeTruthy()

    const agents = Object.entries(json as Record<string, any>)
    expect(agents.length).toBeGreaterThan(0)

    const allowedKeys = new Set([
      'name',
      'version',
      'capabilities',
      'description',
      'metadata',
      'tags',
      'links',
      'status',
    ])

    for (const [agent, config] of agents) {
      expect(typeof agent).toBe('string')
      expect(config && typeof config === 'object').toBeTruthy()

      expect(config).toHaveProperty('name')
      expect(typeof config.name).toBe('string')
      expect((config.name as string).trim().length).toBeGreaterThan(0)

      expect(config).toHaveProperty('version')
      expect(typeof config.version).toBe('string')
      expect((config.version as string).trim().length).toBeGreaterThan(0)

      expect(config).toHaveProperty('capabilities')
      expect(Array.isArray(config.capabilities)).toBeTruthy()
      expect((config.capabilities as unknown[]).length).toBeGreaterThan(0)
      for (const capability of config.capabilities as unknown[]) {
        expect(typeof capability).toBe('string')
        expect((capability as string).trim().length).toBeGreaterThan(0)
      }

      const unexpectedKeys = Object.keys(config).filter(key => !allowedKeys.has(key))
      expect(
        unexpectedKeys,
        `Agent ${agent} exposes unexpected keys: ${unexpectedKeys.join(', ')}`
      ).toHaveLength(0)
    }
  })
})
