/**
 * The welcome question and the expectations (spec 024, AC-024-4, AC-024-5): like the mocks
 * welcome.html, welcome-expect.html and dashboard-expectations.html, three widths, axe, and no
 * sideways scroll at 360 px. Synthetic data only.
 */
import { expect, type Page, test } from '@playwright/test'
import { createRequire } from 'node:module'
import expectations from '../../../contracts/design/fixtures/expectations.json' with { type: 'json' }
import { DASHBOARD, WORKSPACE } from '../../src/widgets/dashboard/dashboard.fixture'
import { CASH, FLOW_PARTIES, FLOW_STATEMENT, LINES } from '../../src/widgets/dashboard/charts.fixture'
import { PNL } from '../../src/widgets/profit-loss/fixture'
import { mockUrl, texts } from './fixtures'

const require = createRequire(import.meta.url)

const SAVED = [
  { month: '2026-09', moneyIn: '150000000.00', moneyOut: '120000000.00' },
  { month: '2026-10', moneyIn: '160000000.00', moneyOut: null },
]

async function serve(page: Page, saved: unknown[] = []) {
  const workspace = { ...WORKSPACE, goal: saved.length ? 'CHECK_EXPECTATIONS' : null, expectations: saved }
  await page.route((url) => url.pathname.startsWith('/api/'), (route) => {
    const url = new URL(route.request().url())
    const path = url.pathname
    if (path === '/api/workspace') return route.fulfill({ json: workspace })
    if (path === '/api/expectations') return route.fulfill({ json: expectations })
    if (path === '/api/dashboard') return route.fulfill({ json: DASHBOARD })
    if (path === '/api/profit-loss') return route.fulfill({ json: PNL })
    if (path === '/api/money-flow') return route.fulfill({ json: url.searchParams.get('view') === 'COUNTERPARTIES' ? FLOW_PARTIES : FLOW_STATEMENT })
    if (path === '/api/cash-flow') return route.fulfill({ json: CASH })
    if (path === '/api/bank-lines') return route.fulfill({ json: LINES })
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

const welcomeOutline = async (page: Page) => ({
  title: await texts(page, '.onboard-form h1'),
  choices: await texts(page, '.welcome-choice'),
  expanded: await page.locator('.welcome-choice').evaluateAll((els) => els.map((el) => el.getAttribute('aria-expanded'))),
  form: await texts(page, '.onboard-form form :is(h2, label, .hint, .button)'),
  values: await page.locator('.onboard-form form input').evaluateAll((els) => els.map((el) => (el as HTMLInputElement).value)),
  skip: await texts(page, '.welcome-skip'),
})

const noSidewaysScroll = (page: Page) => page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)

test('AC-024-4: the welcome question is like the mock, without navigation', async ({ page }) => {
  await serve(page)
  await page.goto('/preview/welcome')
  await expect(page.getByRole('button', { name: /Keep my books/ })).toBeVisible()
  await expect(page.locator('nav')).toHaveCount(0)
  await expect(page.locator('.onboard-form')).toHaveScreenshot('welcome.png')
  expect(await axe(page, '.onboard-form')).toEqual([])
  const implementation = await welcomeOutline(page)
  await page.setViewportSize({ width: 360, height: 800 })
  expect(await noSidewaysScroll(page)).toBeLessThanOrEqual(0)
  await page.goto(mockUrl('welcome'))
  expect(await welcomeOutline(page)).toEqual(implementation)
})

test('AC-024-4: changing the expectations opens the form with what was saved, like the mock', async ({ page }) => {
  await serve(page, SAVED)
  await page.goto('/preview/welcome?expect=1')
  await expect(page.getByRole('heading', { name: 'What you expect' })).toBeVisible()
  await expect(page.getByLabel('Money in').first()).toHaveValue('150000000')
  await expect(page.locator('.onboard-form form')).toHaveScreenshot('welcome-expect.png')
  expect(await axe(page, '.onboard-form')).toEqual([])
  const implementation = await welcomeOutline(page)
  await page.setViewportSize({ width: 360, height: 800 })
  expect(await noSidewaysScroll(page)).toBeLessThanOrEqual(0)
  await page.goto(mockUrl('welcome-expect'))
  expect(await welcomeOutline(page)).toEqual(implementation)
})

const panel = '#content section[aria-labelledby="dash-expect-h"]'
const panelOutline = async (page: Page) => ({
  head: await texts(page, `${panel} .panel-head :is(h2, p, .link)`),
  months: await texts(page, `${panel} .expect-month h3`),
  sides: await texts(page, `${panel} .expect-side`),
  links: await page.locator(`${panel} .expect-links a`).evaluateAll((els) => els.map((el) => el.textContent?.trim())),
})

test('AC-024-5: the dashboard compares the expectations like the mock', async ({ page }) => {
  await serve(page, SAVED)
  await page.clock.setFixedTime(new Date('2026-06-20T03:00:00Z'))
  await page.goto('/preview/shell?period=2026-01..2026-06')
  await expect(page.getByRole('heading', { name: 'What you expected' })).toBeVisible()
  await expect(page.locator(panel)).toHaveScreenshot('dashboard-expectations.png')
  expect(await axe(page, panel)).toEqual([])
  const implementation = await panelOutline(page)
  await page.goto(mockUrl('dashboard-expectations'))
  expect(await panelOutline(page)).toEqual(implementation)
})
