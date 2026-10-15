import { expect, type Page, test } from '@playwright/test'
import { createRequire } from 'node:module'
import { resolve } from 'node:path'
import { pathToFileURL } from 'node:url'
import { EMPTY_PNL, PNL, PNL_ACCOUNTS, PNL_CASH, PNL_CASH_ACCOUNTS } from '../../src/widgets/profit-loss/fixture'

const require = createRequire(import.meta.url)
async function serve(page: Page, empty = false) {
  await page.route((url) => url.pathname.startsWith('/api/'), (route) => {
    const path = new URL(route.request().url()).pathname
    if (path === '/api/profit-loss/accounts') return route.fulfill({ json: empty ? { ...PNL_ACCOUNTS, accounts: [] } : PNL_ACCOUNTS })
    if (path === '/api/profit-loss') return route.fulfill({ json: empty ? EMPTY_PNL : PNL })
    if (path === '/api/months') return route.fulfill({ json: { items: [{ month: '2026-03' }] } })
    return route.fulfill({ json: { items: [] } })
  })
}

/** The same workspace before any ledger export: the report is cash basis from its bank lines. */
async function serveCash(page: Page) {
  await page.route((url) => url.pathname.startsWith('/api/'), (route) => {
    const path = new URL(route.request().url()).pathname
    if (path === '/api/profit-loss/accounts') return route.fulfill({ json: PNL_CASH_ACCOUNTS })
    if (path === '/api/profit-loss') return route.fulfill({ json: PNL_CASH })
    if (path === '/api/months') return route.fulfill({ json: { items: [{ month: '2026-03' }] } })
    return route.fulfill({ json: { items: [] } })
  })
}

test('AC-018-5: company P&L matches the reviewed mock layout', async ({ page }) => {
  await serve(page)
  await page.goto('/preview/profit-loss?period=2026-03')
  await expect(page.getByText('Net profit', { exact: true }).filter({ visible: true })).toBeVisible()
  // Native selects render their text differently from run to run on the phone project; they are masked.
  await expect(page).toHaveScreenshot('profit-loss.png', { fullPage: true, mask: [page.locator('select')] })
  await page.getByRole('button', { name: 'Table', exact: true }).click()
  await expect(page.getByRole('cell', { name: /IDR.*26,000,000/ })).toBeVisible()
  await page.addScriptTag({ path: require.resolve('axe-core/axe.min.js') })
  const violations = await page.evaluate(async () => {
    const axe = (window as unknown as { axe: { run: (context?: string) => Promise<{ violations: { id: string; impact: string }[] }> } }).axe
    return (await axe.run('#content')).violations.filter((v) => v.impact === 'serious' || v.impact === 'critical')
  })
  expect(violations).toEqual([])
})

test('AC-018-5: unavailable data has no invented amounts', async ({ page }) => {
  await serve(page, true)
  await page.goto('/preview/profit-loss?period=2026-03')
  await expect(page.getByText('No general-ledger accounts have been imported.')).toBeVisible()
  await expect(page).toHaveScreenshot('profit-loss-empty.png', { fullPage: true, mask: [page.locator('select')] })
})

test('AC-018-5: boundary widths and classification action remain usable', async ({ page }) => {
  await serve(page)
  await page.goto('/preview/profit-loss?period=2026-03')
  await expect(page.getByText('Net profit', { exact: true }).filter({ visible: true })).toBeVisible()
  for (const width of [360, 1600]) {
    await page.setViewportSize({ width, height: 1000 })
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
    await page.getByLabel('Subledger', { exact: true }).selectOption('GENERAL')
    const button = page.getByRole('button', { name: 'Confirm classification' })
    const box = await button.boundingBox()
    expect(box?.height).toBeGreaterThanOrEqual(width === 360 ? 44 : 40)
    await button.click()
    await expect(page.getByRole('status')).toContainText('Classification confirmed')
  }
})

test('AC-018-7: mock and implementation retain the same report sections and controls', async ({ page }) => {
  await serve(page)
  const read = async () => ({
    headings: await page.locator('#content h1, #content h2, #content h3').allTextContents(),
    views: await page.getByRole('group', { name: 'Profit and loss view', exact: true }).innerText(),
    sources: await page.locator('.pnl-source').allTextContents(),
  })
  await page.goto('/preview/profit-loss?period=2026-03')
  await expect(page.getByText('Source entries', { exact: true })).toBeVisible()
  const implementation = await read()
  await page.goto(pathToFileURL(resolve('../design/mocks/profit-loss.html')).href)
  expect(await read()).toEqual(implementation)
})

test('AC-018-5: source drawer supports keyboard inspection and closes to the selected item', async ({ page }) => {
  await serve(page)
  await page.goto('/preview/profit-loss?period=2026-03')
  const entry = page.getByRole('button', { name: /(?:4000 Sales IDR|^Revenue IDR)/ }).filter({ visible: true }).first()
  await entry.focus()
  await entry.press('Enter')
  const dialog = page.getByRole('dialog')
  await expect(dialog).toContainText('Row 1')
  await expect(dialog).toHaveScreenshot('profit-loss-entries.png')
  await expect(dialog.getByRole('button', { name: 'Close entries' })).toBeFocused()
  await page.keyboard.press('Escape')
  await expect(dialog).toHaveCount(0)
  await expect(entry).toBeFocused()
})

test('AC-018-8: without a ledger export the page reports a cash basis from bank lines like the mock', async ({ page }) => {
  await serveCash(page)
  const read = async () => ({
    headings: await page.locator('#content h1, #content h2, #content h3').allTextContents(),
    basis: await page.locator('#content .chart-head p').allTextContents(),
    coverage: await page.locator('#content .chart-panel > p.muted').allTextContents(),
    notes: await page.locator('#content .chart-panel li').allTextContents(),
    views: await page.getByRole('group', { name: 'Profit and loss view', exact: true }).innerText(),
    categories: await page.locator('#content .pnl-accounts tbody strong').allTextContents(),
    labels: await page.locator('#content .pnl-accounts tbody td:nth-child(3)').allTextContents(),
    sources: await page.locator('.pnl-source').allTextContents(),
  })
  await page.goto('/preview/profit-loss?period=2026-03')
  await expect(page.getByText('Cash-basis report for 2026-03, from your bank lines')).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Category labels' })).toBeVisible()
  await expect(page.getByText('From the category policy')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Confirm classification' })).toHaveCount(0)
  await expect(page).toHaveScreenshot('profit-loss-cash.png', { fullPage: true, mask: [page.locator('select')] })
  const implementation = await read()
  await page.goto(pathToFileURL(resolve('../design/mocks/profit-loss-cash.html')).href)
  expect(await read()).toEqual(implementation)
})
