import { test, expect } from '@playwright/test'

/**
 * Ensures critical security headers are present on the root endpoint.
 */
test.describe('Security :: HTTP Response Headers', () => {
  test('critical security headers must be present', async ({ request }) => {
    const response = await request.get('/')

    const headers = response.headers()

    expect(headers).toHaveProperty('strict-transport-security')
    expect(headers['strict-transport-security']).toMatch(/max-age=\d+/)

    expect(headers).toHaveProperty('x-frame-options')
    expect(headers['x-frame-options'].toUpperCase()).toBe('DENY')

    expect(headers).toHaveProperty('referrer-policy')
    expect(headers['referrer-policy']).toMatch(/no-referrer|strict-origin/)

    expect(headers).toHaveProperty('content-security-policy')
    expect(headers['content-security-policy'].length).toBeGreaterThan(0)
  })
})
