/**
 * The synthetic fixtures the browser checks serve as the API (spec 019): the same JSON files the
 * HTML mocks are generated from (contracts/design/fixtures), so a mock and its screen cannot drift
 * apart silently. Synthetic data only (docs/18).
 */
import { pathToFileURL } from 'node:url'
import { resolve } from 'node:path'
import type { Page } from '@playwright/test'
import counterparties from '../../../contracts/design/fixtures/counterparties.json' with { type: 'json' }
import document from '../../../contracts/design/fixtures/document.json' with { type: 'json' }
import labels from '../../../contracts/design/fixtures/labels.json' with { type: 'json' }
import month from '../../../contracts/design/fixtures/month.json' with { type: 'json' }
import review from '../../../contracts/design/fixtures/review.json' with { type: 'json' }
import risk from '../../../contracts/design/fixtures/risk.json' with { type: 'json' }
import runs from '../../../contracts/design/fixtures/runs.json' with { type: 'json' }

export const COUNTERPARTIES = counterparties
export const DOCUMENT = document
export const MONTH = month
export const REVIEW = review
export const RISK = risk
export const LABELS = labels
export const RUNS = runs

/** The workspace the mocks' shell shows (tools/design/mocks/shell.py). */
export const WORKSPACE = {
  orgId: 'org_synthetic',
  name: 'Sunrise Coffee Roasters',
  currency: 'IDR',
  kind: 'COMPANY',
  profile: { accountingFramework: 'IFRS' },
}

/** A generated mock, opened from the file system. */
export const mockUrl = (name: string) => pathToFileURL(resolve(`../design/mocks/${name}.html`)).href

/** Texts of the elements, trimmed, with a trailing count ("Bank lines 45") removed when asked. */
export async function texts(page: Page, selector: string, dropCounts = false) {
  const all = await page.locator(selector).allTextContents()
  return all.map((s) => s.replace(/\s+/g, ' ').trim()).map((s) => (dropCounts ? s.replace(/\s*\d[\d,. ]*(difference)?$/, '') : s))
}

/**
 * A page image for the app's page viewer: the mock's synthetic page, screenshotted, with the box of
 * its lit value normalized to the page (contracts BBox). Never a real document.
 */
export async function pageImageFromMock(page: Page, mock: string, selector = '.doc-page') {
  await page.goto(mockUrl(mock))
  const figure = page.locator(selector).first()
  const png = await figure.screenshot()
  const box = await page.evaluate((sel) => {
    const fig = document.querySelector(sel)?.getBoundingClientRect()
    const lamp = document.querySelector(`${sel} .lamp`)?.getBoundingClientRect()
    if (!fig || !lamp) return null
    return {
      x0: (lamp.left - fig.left) / fig.width,
      y0: (lamp.top - fig.top) / fig.height,
      x1: (lamp.right - fig.left) / fig.width,
      y1: (lamp.bottom - fig.top) / fig.height,
    }
  }, selector)
  return { png, box }
}
