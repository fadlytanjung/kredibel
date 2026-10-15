/**
 * Risk page parity with its mock (spec 008 AC-008-7, AC-008-10; spec 019 AC-019-4): the same
 * synthetic fixture as design/mocks/risk.html (findings and documents) and the dashboard's months
 * for the strip, three widths, 360/1600 bounds, axe. The strip, the chips, each month's heading,
 * rows, places and statuses are compared.
 */
import { expect, type Page, test } from '@playwright/test'
import { createRequire } from 'node:module'
import { DASHBOARD } from '../../src/widgets/dashboard/dashboard.fixture'
import { mockUrl, RISK, texts, WORKSPACE } from './fixtures'

const require = createRequire(import.meta.url)

async function serve(page: Page) {
  await page.route((url) => url.pathname.startsWith('/api/'), (route) => {
    const path = new URL(route.request().url()).pathname
    if (path === '/api/dashboard') return route.fulfill({ json: DASHBOARD })
    if (path === '/api/findings') return route.fulfill({ json: { items: RISK.findings, nextCursor: null } })
    if (path.startsWith('/api/findings/')) {
      const one = RISK.findings.find((f) => f.findingId === path.split('/').pop())
      return one ? route.fulfill({ json: one }) : route.fulfill({ status: 404, json: { code: 'FINDING_NOT_FOUND' } })
    }
    if (path === '/api/documents') return route.fulfill({ json: { items: RISK.documents, nextCursor: null } })
    if (path === '/api/workspace') return route.fulfill({ json: WORKSPACE })
    return route.fulfill({ json: { items: [] } })
  })
}

async function axeClean(page: Page) {
  await page.addScriptTag({ path: require.resolve('axe-core/axe.min.js') })
  const violations = await page.evaluate(async () => {
    const axe = (window as unknown as { axe: { run: (context?: string) => Promise<{ violations: { id: string; impact: string }[] }> } }).axe
    return (await axe.run('#content')).violations.filter((v) => v.impact === 'serious' || v.impact === 'critical')
  })
  expect(violations).toEqual([])
}

async function noOverflow(page: Page) {
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
  expect(overflow).toBeLessThanOrEqual(0)
}

/** The page as a person sees it: lead, strip, chips, each month's heading, rows, places, statuses. */
async function outline(page: Page) {
  return {
    headings: await texts(page, '#content :is(h1, h2):visible'),
    lead: await texts(page, '#content .page-head p'),
    strip: (await texts(page, '#content .mtab')).map((s) => s.replace(/\s/g, '')), // JSX spacing differs
    chips: await texts(page, '#content .chips .chip'),
    groupBadges: await texts(page, '#content .find-head .badge'),
    openLinks: await texts(page, '#content .find-head .link'),
    columns: await texts(page, '#content .find-table th:visible'),
    rows: await texts(page, '#content .find-table .find-link'),
    places: await texts(page, '#content .find-table td:visible:is(.hide-rt), #content .find-table td .sub:visible'),
    statuses: await texts(page, '#content .find-table .status-line'),
    flagged: await page.locator('#content .find-table tr.is-flagged').count(),
    foot: await texts(page, '#content > .stack > p.muted'),
  }
}

test('AC-008-7: the risk page shows the month strip, the chips and each month\'s findings like the mock', async ({ page }) => {
  await serve(page)
  await page.goto('/preview/risk')
  await expect(page.getByRole('heading', { name: 'Risk' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'March 2026' })).toBeVisible()
  await expect(page.getByRole('link', { name: /Running balance does not add up on 14 Mar/ })).toHaveAttribute('href', '/risk/fnd_mar_a01')
  await expect(page.getByRole('link', { name: 'Open March' })).toHaveAttribute('href', '/months/2026-03')
  await noOverflow(page)
  await expect(page).toHaveScreenshot('risk.png', { fullPage: true })
  await axeClean(page)
  const implementation = await outline(page)
  await page.goto(mockUrl('risk'))
  expect(await outline(page)).toEqual(implementation)
})

test('AC-008-7: the chips filter the findings and the held copies read "Held"', async ({ page }) => {
  await serve(page)
  await page.goto('/preview/risk')
  await expect(page.getByRole('heading', { name: 'March 2026' })).toBeVisible()
  await page.getByRole('button', { name: /^Held copies/ }).click()
  expect(await texts(page, '#content .find-table .status-line')).toEqual(['Held', 'Held', 'Held', 'Held'])
  expect(await texts(page, '#content :is(h2):visible')).toEqual(['March 2026', 'May 2026', 'February 2026', 'June 2026'])
  await page.getByRole('button', { name: /^Critical/ }).click()
  expect(await texts(page, '#content .find-table .find-t')).toEqual(['Running balance does not add up on 14 Mar'])
  await noOverflow(page)
})

test('the page stays inside 360 and 1600 px', async ({ page }) => {
  await serve(page)
  for (const width of [360, 1600]) {
    await page.setViewportSize({ width, height: 900 })
    await page.goto('/preview/risk')
    await expect(page.getByRole('heading', { name: 'March 2026' })).toBeVisible()
    await noOverflow(page)
  }
})
