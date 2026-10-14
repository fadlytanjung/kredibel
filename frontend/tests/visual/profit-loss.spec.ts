import { expect, type Page, test } from '@playwright/test'
import { createRequire } from 'node:module'
import { EMPTY_PNL, PNL, PNL_ACCOUNTS } from '../../src/widgets/profit-loss/fixture'

const require = createRequire(import.meta.url)
async function serve(page: Page, empty = false) {
  await page.route((url) => url.pathname.startsWith('/api/'), (route) => {
    const path = new URL(route.request().url()).pathname
    if (path === '/api/profit-loss/accounts') return route.fulfill({ json: empty ? { ...PNL_ACCOUNTS, accounts: [] } : PNL_ACCOUNTS })
    if (path === '/api/profit-loss') return route.fulfill({ json: empty ? EMPTY_PNL : PNL })
    return route.fulfill({ json: { items: [] } })
  })
}

test('AC-018-5: company P&L matches the reviewed mock layout', async ({ page }) => {
  await serve(page)
  await page.goto('/preview/profit-loss?period=2026-03')
  await expect(page.getByText('Net profit', { exact: true })).toBeVisible()
  await expect(page).toHaveScreenshot('profit-loss.png', { fullPage: true })
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
  await expect(page).toHaveScreenshot('profit-loss-empty.png', { fullPage: true })
})

test('AC-018-5: boundary widths and classification action remain usable', async ({ page }) => {
  await serve(page)
  await page.goto('/preview/profit-loss?period=2026-03')
  await expect(page.getByText('Net profit', { exact: true })).toBeVisible()
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
