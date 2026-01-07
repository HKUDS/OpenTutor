import { expect, APIResponse } from '@playwright/test'
import { createHash } from 'crypto'

type CleanErrorOptions = {
  allowEmpty?: boolean
}

type MarkdownStructureOptions = {
  requireTopHeading?: boolean
  requireSecondaryHeadingForLongForm?: boolean
  secondaryHeadingThreshold?: number
}

/**
 * Centralised validator utilities that enforce API hygiene and documentation
 * quality gates across the Deep audit suite.
 */
export class ArchitectureValidator {
  static async assertCleanError(
    response: APIResponse,
    options?: CleanErrorOptions
  ): Promise<string> {
    const text = await response.text()
    this.assertCleanErrorText(text, options)
    return text
  }

  static assertCleanErrorText(text: string, { allowEmpty = false }: CleanErrorOptions = {}): void {
    if (!text) {
      expect(allowEmpty).toBeTruthy()
      return
    }

    const hasTracebackHeader = /Traceback\s\(most\srecent\scall\slast\)/i.test(text)
    const hasExceptionToken =
      /(\b[A-Z][a-zA-Z]+Error:|Exception:|fastapi\.exceptions|uvicorn\.error)/.test(text)
    const hasStackFrame = /\bFile\s"[^"]+\.(py|ts|js)"/i.test(text)

    const leakedInternals = hasTracebackHeader && (hasExceptionToken || hasStackFrame)

    const digest = createHash('sha256').update(text).digest('hex').slice(0, 16)

    expect(
      leakedInternals,
      `Security violation: API response leaked traceback markers (digest:${digest})`
    ).toBe(false)
  }

  static assertCitationDensity(content: string, minMatchesPerThousand: number = 3): void {
    if (!content || content.length < 200) {
      return
    }

    const citationPattern = /\[[\d\-\,\s]+\]|\([\w\s\.]+,\s?\d{4}\)|\bETA:\s*\d{4}\b/g
    const matches = content.match(citationPattern) || []
    const density = (matches.length / content.length) * 1000

    expect(density).toBeGreaterThanOrEqual(minMatchesPerThousand)
  }

  static assertMarkdownStructure(content: string, options: MarkdownStructureOptions = {}): void {
    const {
      requireTopHeading = true,
      requireSecondaryHeadingForLongForm = true,
      secondaryHeadingThreshold = 500,
    } = options

    if (requireTopHeading) {
      expect(content).toMatch(/^#\s/m)
    }

    if (requireSecondaryHeadingForLongForm && content.length > secondaryHeadingThreshold) {
      expect(content).toMatch(/^##\s/m)
    }
  }
}
