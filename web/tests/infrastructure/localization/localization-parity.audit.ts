import { test, expect } from '@playwright/test'
import fs from 'fs/promises'
import path from 'path'

/**
 * COMPLIANCE AUDIT: Instruction Drift (v0.3.0 Aligned)
 * Ensures localized agent prompts maintain structural parity with the English source.
 */
test.describe('Infrastructure :: Prompt Consistency', () => {
  const PROMPTS_ROOT = path.resolve(__dirname, '../../../src/agents')

  test('localized prompts must maintain structural parity with source', async () => {
    const modulePath = path.join(PROMPTS_ROOT, 'research/prompts')

    try {
      await fs.access(modulePath)
    } catch {
      test.skip(true, 'Agent source not accessible; environment likely lacks mounted src volume.')
      return
    }

    const enDir = path.join(modulePath, 'en')
    try {
      await fs.access(enDir)
    } catch {
      throw new Error('English source directory is missing')
    }

    const localizedEntries = await fs.readdir(modulePath, { withFileTypes: true })
    const localizedLangs = localizedEntries
      .filter(entry => entry.isDirectory() && entry.name !== 'en')
      .map(entry => entry.name)

    const enFiles = (await fs.readdir(enDir)).filter(f => f.endsWith('.yaml'))
    const enFileSet = new Set(enFiles)

    if (enFiles.length !== enFileSet.size) {
      throw new Error('Duplicate YAML files detected in English source directory')
    }

    for (const lang of localizedLangs) {
      const langDir = path.join(modulePath, lang)
      const langFiles = (await fs.readdir(langDir)).filter(f => f.endsWith('.yaml'))
      const langFileSet = new Set(langFiles)

      expect(langFileSet.size, `Locale [${lang}] has duplicate YAML files`).toBe(langFiles.length)

      const missing = [...enFileSet].filter(file => !langFileSet.has(file))
      const extra = [...langFileSet].filter(file => !enFileSet.has(file))

      expect(missing, `Locale [${lang}] is missing YAML files: ${missing.join(', ')}`).toHaveLength(
        0
      )
      expect(
        extra,
        `Locale [${lang}] includes unexpected YAML files: ${extra.join(', ')}`
      ).toHaveLength(0)

      for (const file of enFiles) {
        const [enContent, langContent] = await Promise.all([
          fs.readFile(path.join(enDir, file), 'utf-8'),
          fs.readFile(path.join(langDir, file), 'utf-8'),
        ])

        ;['system:', 'user_template:', 'Output Format:'].forEach(key => {
          if (enContent.includes(key)) {
            expect(
              langContent.includes(key),
              `Drift in ${file} [${lang}]: Missing core block '${key}'`
            ).toBeTruthy()
          }
        })
      }
    }
  })
})
