/**
 * Month and all-months parity with their mocks (spec 019, T019-03, AC-019-3, AC-019-4; spec 007
 * AC-007-12…19, spec 008 AC-008-6): the figures, the explained risk with its citation chips, the
 * match meter, the bank lines with their support and actions, and the months table.
 */
import { expect, type Page, test } from '@playwright/test'
import { createRequire } from 'node:module'
import { mockUrl, MONTH, texts, WORKSPACE } from './fixtures'

const require = createRequire(import.meta.url)

async function serve(page: Page) {
  await page.route((url) => url.pathname.startsWith('/api/'), (route) => {
    const path = new URL(route.request().url()).pathname
    if (path === '/api/months/2026-03') return route.fulfill({ json: MONTH.month })
    if (path === '/api/months') return route.fulfill({ json: { items: MONTH.months } })
    if (path === '/api/bank-lines') return route.fulfill({ json: { items: MONTH.lines, nextCursor: null } })
    if (path === '/api/matches') return route.fulfill({ json: { items: MONTH.matches } })
    if (path === '/api/invoices') return route.fulfill({ json: { items: MONTH.invoices } })
    if (path === '/api/receipts') return route.fulfill({ json: { items: MONTH.receipts } })
    if (path === '/api/findings') return route.fulfill({ json: { items: MONTH.findings } })
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

/** What a person sees on the month page: header, figures, explanation, tabs, filters, columns, rows. */
async function outline(page: Page) {
  return {
    headings: await texts(page, '#content :is(h1, h2, h3):visible'),
    head: await texts(page, '#content .month-head .badge, #content .month-head .link, #content .month-head .button'),
    figures: await texts(page, '#content .ledger-figures dt'),
    citations: await texts(page, '#content .explain .citation'),
    steps: await texts(page, '#content .explain .steps li'),
    meter: await texts(page, '#content .recon-meter .key span'),
    tabs: await texts(page, '#content [role="tab"]', true),
    chips: await texts(page, '#content .chips .chip', true),
    toolbar: await texts(page, '#content .table-actions .button'),
    columns: await texts(page, '#content .data-table th'),
    support: await texts(page, '#content .data-table .match-chip'),
    actions: await texts(page, '#content .data-table .button'),
    legend: await texts(page, '#content .reading-legend'),
  }
}

async function openMarch(page: Page) {
  await serve(page)
  await page.goto('/preview/months/2026-03')
  await expect(page.getByRole('heading', { name: 'March 2026' })).toBeVisible()
  await expect(page.getByText('Critical risk this month')).toBeVisible()
  await expect(page.getByRole('cell', { name: /TRANSFER IN HARBORVIEW HOTEL GROUP|Harborview Hotel Group/ }).first()).toBeVisible()
}

test('AC-019-3: March shows its figures, the explained risk with citations, the meter and its bank lines like the mock', async ({ page }) => {
  await openMarch(page)
  // The explainer's finding markers are citation chips that open the evidence (AC-008-6).
  await expect(page.getByRole('link', { name: 'A01' })).toHaveAttribute('href', '/risk/fnd_a01_mar')
  await expect(page.locator('#content .explain')).not.toContainText('[[')
  await expect(page).toHaveScreenshot('month.png', { fullPage: true })
  await axeClean(page)
  const implementation = await outline(page)
  await page.goto(mockUrl('month'))
  expect(await outline(page)).toEqual(implementation)
})

test('AC-019-3: all months list their state, risk and statements like the mock', async ({ page }) => {
  await serve(page)
  await page.goto('/preview/months')
  await expect(page.getByRole('heading', { name: 'Months in this workspace' })).toBeVisible()
  await expect(page.getByRole('cell', { name: /March 2026/ })).toBeVisible()
  await expect(page).toHaveScreenshot('months.png', { fullPage: true })
  await axeClean(page)
  const read = async () => ({
    headings: await texts(page, '#content :is(h1, h2):visible'),
    chips: await texts(page, '#content .chips .chip', true),
    columns: await texts(page, '#content .data-table th'),
    months: await texts(page, '#content .data-table tbody strong'),
    badges: await texts(page, '#content .data-table tbody .badge'),
  })
  const implementation = await read()
  await page.goto(mockUrl('months'))
  expect(await read()).toEqual(implementation)
})

test('AC-019-4: the month page stays inside 360 and 1600 px and its actions remain usable', async ({ page }) => {
  await openMarch(page)
  for (const width of [360, 1600]) {
    await page.setViewportSize({ width, height: 1000 })
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
    const match = page.getByRole('button', { name: 'Match', exact: true }).first()
    await match.scrollIntoViewIfNeeded()
    const box = await match.boundingBox()
    expect(box?.height ?? 0).toBeGreaterThanOrEqual(32)
    const findings = page.getByRole('tab', { name: /Findings/ })
    await findings.click()
    await expect(findings).toHaveAttribute('aria-selected', 'true')
    await page.getByRole('tab', { name: /Bank lines/ }).click()
  }
})
