/**
 * Dashboard parity with its mock (spec 019, T019-02, AC-019-2, AC-019-4; spec 010, T010-06):
 * the same synthetic fixture as design/mocks/dashboard.html, three widths, 360/1600 bounds, axe.
 */
import { expect, type Page, test } from '@playwright/test'
import { createRequire } from 'node:module'
import { resolve } from 'node:path'
import { pathToFileURL } from 'node:url'
import { DASHBOARD, WORKSPACE } from '../../src/widgets/dashboard/dashboard.fixture'
import { COUNTERPARTIES } from './fixtures'
import { CASH, FLOW_PARTIES, FLOW_STATEMENT, LINES } from '../../src/widgets/dashboard/charts.fixture'
import { PNL } from '../../src/widgets/profit-loss/fixture'

const require = createRequire(import.meta.url)

async function serve(page: Page, dashboard: unknown = DASHBOARD) {
  await page.route((url) => url.pathname.startsWith('/api/'), (route) => {
    const url = new URL(route.request().url())
    const path = url.pathname
    if (path === '/api/dashboard') return route.fulfill({ json: dashboard })
    if (path === '/api/workspace') return route.fulfill({ json: WORKSPACE })
    if (path === '/api/profit-loss') return route.fulfill({ json: PNL })
    if (path === '/api/money-flow') return route.fulfill({ json: url.searchParams.get('view') === 'COUNTERPARTIES' ? FLOW_PARTIES : FLOW_STATEMENT })
    if (path === '/api/cash-flow') return route.fulfill({ json: CASH })
    if (path === '/api/bank-lines') return route.fulfill({ json: LINES })
    if (path === '/api/suggestions') return route.fulfill({ json: { items: COUNTERPARTIES.suggestions } })
    return route.fulfill({ json: { items: [] } })
  })
}

/** The dashboard's outline as a person sees it at this width: the visible headings, segmented
 *  controls and panel links, in order (the mock keeps hidden copies for its framework switch). */
async function outline(page: Page) {
  return {
    headings: (await page.locator('#content :is(h1, h2, h3):visible').allTextContents()).map((s) => s.trim()),
    controls: await page.locator('#content .seg[role="group"]:visible').evaluateAll((els) => els.map((el) => `${el.getAttribute('aria-label')}: ${Array.from(el.querySelectorAll('button')).map((b) => b.textContent?.trim()).join(' | ')}`)),
    panelLinks: (await page.locator('#content :is(.panel-head .link, .section-head .link, .section-head .button):visible').allTextContents()).map((s) => s.trim()),
  }
}

async function open(page: Page) {
  await serve(page)
  await page.goto('/preview/shell')
  await page.getByRole('button', { name: 'All months', exact: true }).click()
  await expect(page.getByText('2 of 6 months are reconciled.')).toBeVisible()
  // The flow has loaded at every width once its unit note is printed (phones draw ranked bars, not the Sankey).
  await expect(page.getByRole('region', { name: 'Money flow' }).getByText(/Amounts in millions/)).toBeVisible()
}

test('AC-019-2: the dashboard matches the reviewed mock layout', async ({ page }) => {
  await open(page)
  await expect(page).toHaveScreenshot('dashboard.png', { fullPage: true })
  await page.addScriptTag({ path: require.resolve('axe-core/axe.min.js') })
  const violations = await page.evaluate(async () => {
    const axe = (window as unknown as { axe: { run: (context?: string) => Promise<{ violations: { id: string; impact: string }[] }> } }).axe
    return (await axe.run('#content')).violations.filter((v) => v.impact === 'serious' || v.impact === 'critical')
  })
  expect(violations).toEqual([])
})

test('AC-019-2: mock and implementation keep the same sections, controls and links', async ({ page }) => {
  await open(page)
  const implementation = await outline(page)
  await page.goto(pathToFileURL(resolve('../design/mocks/dashboard.html')).href)
  expect(await outline(page)).toEqual(implementation)
})

test('AC-019-4: the dashboard stays inside 360 and 1600 px and its controls remain usable', async ({ page }) => {
  await open(page)
  for (const width of [360, 1600]) {
    await page.setViewportSize({ width, height: 1000 })
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
    const framework = page.getByRole('group', { name: 'Framework', exact: true }).getByRole('button', { name: 'US GAAP' })
    await framework.click()
    await expect(framework).toHaveAttribute('aria-pressed', 'true')
    const seeMonth = page.getByRole('link', { name: 'See March' })
    const box = await seeMonth.boundingBox()
    expect(box?.height ?? 0).toBeGreaterThanOrEqual(32)
  }
})

test('AC-010-3: a workspace without months sees the upload empty state, never invented figures', async ({ page }) => {
  await serve(page, { ...DASHBOARD, periodMonths: [], kpis: [], months: [], alerts: [], reviewPreview: [] })
  await page.goto('/preview/shell')
  await expect(page.getByText('Upload your first documents')).toBeVisible()
  await expect(page.getByText('1,355,800,000')).toHaveCount(0)
})
