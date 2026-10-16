/**
 * The guided tour (spec 021, AC-021-4…6) over the shell previews: it starts from the address, opens
 * each page, lights its part with the card beside it (at the bottom on phones), shows the months
 * that have books, moves with Next, Back and the arrows, and ends with Esc. The figures step is
 * compared with the mock tour.html at three widths. Synthetic fixtures only.
 */
import { expect, type Page, test } from '@playwright/test'
import { createRequire } from 'node:module'
import { DASHBOARD, WORKSPACE } from '../../src/widgets/dashboard/dashboard.fixture'
import { CASH, FLOW_STATEMENT, LINES } from '../../src/widgets/dashboard/charts.fixture'
import { PNL } from '../../src/widgets/profit-loss/fixture'
import { COUNTERPARTIES, LABELS, MONTH, mockUrl, REVIEW, RISK, RUNS, texts, UPLOADS } from './fixtures'

const require = createRequire(import.meta.url)

async function serve(page: Page) {
  await page.clock.setFixedTime(new Date('2026-06-20T03:00:00Z'))
  await page.route((url) => url.pathname.startsWith('/api/'), (route) => {
    const path = new URL(route.request().url()).pathname
    if (path === '/api/dashboard') return route.fulfill({ json: DASHBOARD })
    if (path === '/api/workspace') return route.fulfill({ json: WORKSPACE })
    if (path === '/api/profit-loss') return route.fulfill({ json: PNL })
    if (path === '/api/money-flow') return route.fulfill({ json: FLOW_STATEMENT })
    if (path === '/api/cash-flow') return route.fulfill({ json: CASH })
    if (path === '/api/bank-lines') return route.fulfill({ json: LINES })
    if (path === '/api/documents') return route.fulfill({ json: { items: UPLOADS.items, nextCursor: null } })
    if (path === '/api/months') return route.fulfill({ json: { items: MONTH.months } })
    if (path === '/api/review-items') return route.fulfill({ json: { items: REVIEW.items, nextCursor: null } })
    if (path === '/api/findings') return route.fulfill({ json: { items: RISK.findings, nextCursor: null } })
    if (path === '/api/counterparties') return route.fulfill({ json: { items: COUNTERPARTIES.counterparties, nextCursor: null } })
    if (path === '/api/labels') return route.fulfill({ json: LABELS })
    if (path === '/api/runs') return route.fulfill({ json: { items: RUNS.items, nextCursor: null } })
    return route.fulfill({ json: { items: [] } })
  })
}

const card = (page: Page) => page.getByRole('dialog', { name: /./ })

async function boxes(page: Page, part: string) {
  const spot = await page.locator('.tour-spot').boundingBox()
  const target = await page.locator(part).first().boundingBox()
  return { spot, target }
}

test('AC-021-4: the tour lights the figures with its card like the mock', async ({ page }) => {
  await serve(page)
  await page.goto('/preview/tour/dashboard?tour=1')
  await expect(card(page).getByRole('heading', { name: 'Welcome to Sunrise Coffee Roasters' })).toBeVisible()
  await expect(page).toHaveURL(/\/preview\/tour\/dashboard\?period=2026-01\.\.2026-06$/)
  await card(page).getByRole('button', { name: 'Next', exact: true }).click()
  await card(page).getByRole('button', { name: 'Next', exact: true }).click()
  await expect(card(page).getByRole('heading', { name: 'The figures' })).toBeFocused()
  const { spot, target } = await boxes(page, '#content .dash .ledger')
  expect(spot && target && Math.abs(spot.x - (target.x - 8)) <= 1 && Math.abs(spot.width - (target.width + 16)) <= 1).toBe(true)
  await expect(page).toHaveScreenshot('tour-figures.png')
  await page.addScriptTag({ path: require.resolve('axe-core/axe.min.js') })
  const violations = await page.evaluate(async () => {
    const axe = (window as unknown as { axe: { run: (context?: string) => Promise<{ violations: { id: string; impact: string }[] }> } }).axe
    return (await axe.run('.tour')).violations.filter((v) => v.impact === 'serious' || v.impact === 'critical')
  })
  expect(violations).toEqual([])
  const implementation = await texts(page, '.tour-card :is(.tour-step, h2, p, .button)')
  await page.goto(mockUrl('tour'))
  expect(await texts(page, '.tour-card :is(.tour-step, h2, p, .button)')).toEqual(implementation)
})

test('AC-021-4: Next opens the next page and lights its part; Back and the arrows move; Esc ends', async ({ page }) => {
  await serve(page)
  await page.goto('/preview/tour/dashboard?tour=1')
  await expect(card(page)).toContainText('Step 1 of 12')
  for (let i = 0; i < 4; i += 1) await page.keyboard.press('ArrowRight')
  await expect(page).toHaveURL(/\/preview\/tour\/documents$/)
  await expect(card(page).getByRole('heading', { name: 'Upload anything, in any order' })).toBeVisible()
  await expect(page.locator('.tour-spot')).toBeVisible()
  await page.keyboard.press('ArrowLeft')
  await expect(card(page).getByRole('heading', { name: 'Where the money went' })).toBeVisible()
  await page.keyboard.press('Escape')
  await expect(page.locator('.tour')).toHaveCount(0)
})

test('AC-021-6: on a phone the card sits at the bottom and the page stays inside the screen', async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 780 })
  await serve(page)
  await page.goto('/preview/tour/dashboard?tour=1')
  await card(page).getByRole('button', { name: 'Next', exact: true }).click()
  await card(page).getByRole('button', { name: 'Next', exact: true }).click()
  const box = await page.locator('.tour-card').boundingBox()
  expect(box && Math.abs(box.y + box.height - (780 - 16)) <= 1).toBe(true)
  expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(0)
})

test('AC-021-4: every step opens its page and lights its part', async ({ page }) => {
  test.setTimeout(90_000)
  await serve(page)
  await page.goto('/preview/tour/dashboard?tour=1')
  const lit = ['period', 'figures', 'flow', 'upload', 'months', 'review', 'risk', 'labels', 'runs', 'assistant']
  const titles: string[] = []
  for (let step = 1; step <= 12; step += 1) {
    await expect(card(page)).toContainText(`Step ${step} of 12`)
    titles.push((await card(page).getByRole('heading').textContent()) ?? '')
    if (step > 1 && step <= lit.length + 1) await expect(page.locator('.tour-spot'), `step ${step} lights its part`).toBeVisible({ timeout: 8000 })
    if (step < 12) await card(page).getByRole('button', { name: 'Next', exact: true }).click()
  }
  expect(titles.at(-1)).toBe('You are ready')
  await card(page).getByRole('button', { name: 'Done' }).click()
  await expect(page.locator('.tour')).toHaveCount(0)
})

