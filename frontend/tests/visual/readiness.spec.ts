/**
 * The loan readiness report (spec 025, AC-025-4): like the mock readiness.html from the same
 * fixture, three widths, axe, no sideways scroll at 360 px; printed without the app's menus.
 * Synthetic data only.
 */
import { expect, type Page, test } from '@playwright/test'
import { createRequire } from 'node:module'
import fixture from '../../../contracts/design/fixtures/readiness.json' with { type: 'json' }
import { WORKSPACE } from '../../src/widgets/dashboard/dashboard.fixture'
import { mockUrl, texts } from './fixtures'

const require = createRequire(import.meta.url)

async function serve(page: Page) {
  await page.route((url) => url.pathname.startsWith('/api/'), (route) => {
    const path = new URL(route.request().url()).pathname
    if (path === '/api/workspace') return route.fulfill({ json: WORKSPACE })
    if (path === '/api/readiness') return route.fulfill({ json: fixture })
    return route.fulfill({ json: { items: [] } })
  })
}

async function axe(page: Page, context: string) {
  await page.addScriptTag({ path: require.resolve('axe-core/axe.min.js') })
  return page.evaluate(async (ctx) => {
    const run = (window as unknown as { axe: { run: (context?: string) => Promise<{ violations: { id: string; impact: string }[] }> } }).axe
    return (await run.run(ctx)).violations.filter((v) => v.impact === 'serious' || v.impact === 'critical')
  }, context)
}

const outline = async (page: Page) => ({
  head: await texts(page, '#content .page-head :is(h1, p, .button)'),
  verdict: await texts(page, '#content .ready-verdict-head :is(.badge, h2, p)'),
  checks: await texts(page, '#content .ready-check :is(.status-line, h3, p, .ready-findings li, .ready-check-body > .link)'),
  note: await texts(page, '#content .ready-note'),
  figures: await texts(page, '#content .ledger-figures > div'),
  columns: await texts(page, '#content .ready-table th'),
  cells: await texts(page, '#content .ready-table tbody td'),
  explained: await texts(page, '#content .ready-explained li'),
  clients: await texts(page, '#content .ready-clients li'),
  documents: await texts(page, '#content .ready-docs li'),
  headings: await texts(page, '#content :is(h2, h3)'),
  nav: await texts(page, '.side .nav .nav-label-long'),
})

test('AC-025-4: the loan readiness report is like the mock', async ({ page }) => {
  await serve(page)
  await page.goto('/preview/readiness')
  await expect(page.getByRole('heading', { name: 'Loan readiness', level: 1 })).toBeVisible()
  await expect(page.getByText('Fix 3 things before you show a lender.')).toBeVisible()
  await expect(page.getByRole('link', { name: /August 2026: The running balance breaks/ })).toHaveAttribute('href', '/risk/fnd_a01_aug')
  await expect(page.locator('#content')).toHaveScreenshot('readiness.png')
  expect(await axe(page, '#content')).toEqual([])
  const implementation = await outline(page)
  await page.setViewportSize({ width: 360, height: 800 })
  expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(0)
  await page.setViewportSize({ width: 1600, height: 900 })
  expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(0)
  await page.goto(mockUrl('readiness'))
  expect(await outline(page)).toEqual(implementation)
})

test('AC-025-4: printed, the report leaves out the menus and the print button', async ({ page }) => {
  await serve(page)
  await page.goto('/preview/readiness')
  await expect(page.getByText('Fix 3 things before you show a lender.')).toBeVisible()
  await page.emulateMedia({ media: 'print' })
  for (const chrome of ['.side', '.topbar', '.dock']) {
    for (const el of await page.locator(chrome).all()) await expect(el).toBeHidden()
  }
  await expect(page.getByRole('button', { name: 'Print or save as PDF' })).toBeHidden()
  await expect(page.getByRole('heading', { name: 'Month by month' })).toBeVisible()
  // The report takes the page's width, not the hidden sidebar's column.
  const width = page.viewportSize()?.width ?? 0
  expect((await page.locator('#content').boundingBox())?.width ?? 0).toBeGreaterThan(width * 0.9)
})
