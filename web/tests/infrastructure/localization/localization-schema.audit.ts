import { test, expect } from '@playwright/test'
import fs from 'fs/promises'
import path from 'path'
import yaml from 'js-yaml'

/**
 * Validates structural parity and placeholder integrity across localized YAML files.
 */
test.describe('Infrastructure :: Localization YAML Schema', () => {
  const ROOT = path.resolve(__dirname, '../../../src/agents/research/prompts')

  test('all localized YAML files parse cleanly and match schema', async () => {
    const dirs = await fs.readdir(ROOT, { withFileTypes: true })
    const langs = dirs.filter(d => d.isDirectory()).map(d => d.name)

    const enDir = path.join(ROOT, 'en')
    const enFiles = (await fs.readdir(enDir)).filter(f => f.endsWith('.yaml'))

    for (const lang of langs) {
      const langDir = path.join(ROOT, lang)
      const langFiles = (await fs.readdir(langDir)).filter(f => f.endsWith('.yaml'))

      expect(langFiles.sort()).toEqual(enFiles.sort())

      for (const file of enFiles) {
        const enContent = yaml.load(await fs.readFile(path.join(enDir, file), 'utf8'))
        const langContent = yaml.load(await fs.readFile(path.join(langDir, file), 'utf8'))

        expect(typeof enContent).toBe('object')
        expect(typeof langContent).toBe('object')

        const enDoc = enContent as Record<string, unknown>
        const langDoc = langContent as Record<string, unknown>

        expect(Object.keys(langDoc).sort()).toEqual(Object.keys(enDoc).sort())

        for (const [key, value] of Object.entries(langDoc)) {
          if (typeof value === 'string') {
            expect(value.trim().length).toBeGreaterThan(0)
            expect(value).not.toMatch(/\bTODO\b|\bTBD\b/i)
            if (lang !== 'en') {
              const englishValue = enDoc[key]
              if (typeof englishValue === 'string' && englishValue.trim().length > 10) {
                expect(value).not.toBe(englishValue)
              }
            }
          }
        }

        const extractPlaceholders = (s: string) => [...s.matchAll(/\{\{[^}]+\}\}/g)].map(m => m[0])

        const enPlaceholders = new Set(
          Object.values(enDoc)
            .filter(v => typeof v === 'string')
            .flatMap(v => extractPlaceholders(v as string))
        )

        const langPlaceholders = new Set(
          Object.values(langDoc)
            .filter(v => typeof v === 'string')
            .flatMap(v => extractPlaceholders(v as string))
        )

        expect([...langPlaceholders].sort()).toEqual([...enPlaceholders].sort())

        const listKeys = Object.entries(enDoc)
          .filter(([, value]) => Array.isArray(value))
          .map(([listKey]) => listKey)

        for (const key of listKeys) {
          const enList = enDoc[key]
          const langList = langDoc[key]

          if (Array.isArray(enList) && Array.isArray(langList)) {
            expect(langList.length).toBe(enList.length)
          }
        }
      }
    }
  })
})
