/**
 * The Transactions table and its drawer (spec 024, AC-024-6): like the mocks transactions.html and
 * transaction.html from the same fixture, three widths, axe, no sideways scroll at 360 px.
 * Synthetic data only.
 */
import { expect, type Page, test } from '@playwright/test'
import { createRequire } from 'node:module'
import fixture from '../../../contracts/design/fixtures/transactions.json' with { type: 'json' }
import { WORKSPACE } from '../../src/widgets/dashboard/dashboard.fixture'
import { mockUrl, texts } from './fixtures'

const require = createRequire(import.meta.url)
const MONTHS = ['2026-03', '2026-04', '2026-05'].map((month) => ({ month, state: 'RECONCILED', figures: {}, statements: [{ docId: `doc_st_${month}` }] }))

async function serve(page: Page) {
  await page.route((url) => url.pathname.startsWith('/api/'), (route) => {
    const path = new URL(route.request().url()).pathname
    if (path === '/api/workspace') return route.fulfill({ json: WORKSPACE })
    if (path === '/api/months') return route.fulfill({ json: { items: MONTHS } })
    if (path === '/api/transactions') return route.fulfill({ json: fixture })
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

const tableOutline = async (page: Page) => ({
  head: await texts(page, '#content .page-head :is(h1, p)'),
  chips: await texts(page, '#content .chips .chip'),
  columns: await texts(page, '#content .data-table th'),
  cells: await texts(page, '#content .data-table tbody td'),
  pager: await texts(page, '#content .pager-line'),
  month: await page.locator('#content .table-toolbar select').evaluate((el) => (el as HTMLSelectElement).selectedOptions[0]?.textContent?.trim()),
  nav: await texts(page, '.side .nav .nav-label-long'),
})

const drawerOutline = async (page: Page) => ({
  head: await texts(page, '.drawer .drawer-head :is(span, h1, p)'),
  facts: await texts(page, '.drawer .tx-facts > div'),
  matched: await texts(page, '.drawer :is(.match-chip, .tx-records li, .actions .button)'),
})

test('AC-024-6: the Transactions table is like the mock', async ({ page }) => {
  await serve(page)
  await page.goto('/preview/transactions?month=2026-05')
  await expect(page.getByRole('heading', { name: 'Transactions', level: 1 })).toBeVisible()
  await expect(page.getByText('Spice Route Restaurant', { exact: true })).toBeVisible()
  await expect(page.locator('#content')).toHaveScreenshot('transactions.png')
  expect(await axe(page, '#content')).toEqual([])
  const implementation = await tableOutline(page)
  await page.setViewportSize({ width: 360, height: 800 })
  expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(0)
  await page.goto(mockUrl('transactions'))
  expect(await tableOutline(page)).toEqual(implementation)
})

test('AC-024-6: a transaction opens in the drawer like the mock', async ({ page }) => {
  await serve(page)
  await page.goto('/preview/transactions?month=2026-05')
  await page.getByText('Spice Route Restaurant', { exact: true }).click()
  const drawer = page.getByRole('dialog')
  await expect(drawer.getByRole('heading', { level: 1 })).toHaveText('INSTANT TRANSFER IN SPICE ROUTE RESTAURANT INV/SCR/2026/05/0011')
  await expect(drawer.getByRole('link', { name: 'Invoice INV/SCR/2026/05/0011' })).toHaveAttribute('href', '/documents/doc_inv_scr_0511')
  await expect(page.locator('.drawer')).toHaveScreenshot('transaction.png')
  expect(await axe(page, '.drawer')).toEqual([])
  const implementation = await drawerOutline(page)
  await page.goto(mockUrl('transaction'))
  expect(await drawerOutline(page)).toEqual(implementation)
})
