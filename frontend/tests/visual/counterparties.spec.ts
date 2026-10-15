/**
 * Clients and suppliers parity with their mocks (spec 014, T014-04, AC-014-2; spec 019 AC-019-4):
 * the same synthetic fixture as design/mocks/clients.html and counterparty.html, three widths,
 * 360/1600 bounds, axe. The list's chips, columns and flags and the detail's panels are compared.
 */
import { expect, type Page, test } from '@playwright/test'
import { createRequire } from 'node:module'
import { COUNTERPARTIES, mockUrl, texts, WORKSPACE } from './fixtures'

const require = createRequire(import.meta.url)
const DETAIL = COUNTERPARTIES.detail

async function serve(page: Page) {
  await page.route((url) => url.pathname.startsWith('/api/'), (route) => {
    const path = new URL(route.request().url()).pathname
    if (path === '/api/counterparties') return route.fulfill({ json: { items: COUNTERPARTIES.counterparties, nextCursor: null } })
    if (path.startsWith('/api/counterparties/')) {
      const party = COUNTERPARTIES.counterparties.find((p) => p.counterpartyId === path.split('/').pop())
      return party ? route.fulfill({ json: party }) : route.fulfill({ status: 404, json: { code: 'COUNTERPARTY_NOT_FOUND' } })
    }
    if (path === '/api/bank-lines') return route.fulfill({ json: { items: DETAIL.lines, nextCursor: null, total: { amount: '-48500000.00', currency: 'IDR' } } })
    if (path === '/api/invoices') return route.fulfill({ json: { items: DETAIL.invoices, nextCursor: null } })
    if (path === '/api/receipts') return route.fulfill({ json: { items: DETAIL.receipts, nextCursor: null } })
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

/** The list as a person sees it: heading, chips, columns, the flagged rows and their badges. */
async function listOutline(page: Page) {
  return {
    headings: await texts(page, '#content :is(h1, h2):visible'),
    chips: await texts(page, '#content .chips .chip', true),
    columns: await texts(page, '#content .data-table th:visible'),
    names: await texts(page, '#content .data-table .doc-cell strong'),
    flags: await texts(page, '#content .data-table .badge'),
    flagged: await page.locator('#content .data-table tr.is-flagged').count(),
  }
}

/** The detail as a person sees it: name, figures, panels and their columns. */
async function detailOutline(page: Page) {
  return {
    headings: await texts(page, '#content :is(h1, h2):visible'),
    figures: await texts(page, '#content .ledger-figures dt'),
    columns: await texts(page, '#content .data-table th:visible'),
    accounts: await texts(page, '#content [aria-labelledby="cp-accounts-h"] tbody td:first-child'),
  }
}

test('AC-014-2: the clients and suppliers list shows roles, amounts, shares, transfers and flagged accounts like the mock', async ({ page }) => {
  await serve(page)
  await page.goto('/preview/counterparties')
  await expect(page.getByRole('heading', { name: 'Clients and suppliers' })).toBeVisible()
  await expect(page.getByRole('cell', { name: /Roastline Equipment Service/ })).toBeVisible()
  await expect(page.getByRole('link', { name: /New account in May \(X08\)/ })).toHaveAttribute('href', '/risk')
  await expect(page.getByRole('link', { name: /2 invoices, never paid \(R02\)/ })).toHaveAttribute('href', '/risk')
  await noOverflow(page)
  await expect(page).toHaveScreenshot('counterparties.png', { fullPage: true })
  await axeClean(page)
  const implementation = await listOutline(page)
  await page.goto(mockUrl('clients'))
  expect(await listOutline(page)).toEqual(implementation)
})

test('AC-014-2: the role chips filter the list', async ({ page }) => {
  await serve(page)
  await page.goto('/preview/counterparties')
  await page.getByRole('group', { name: 'Filter by role' }).getByRole('button', { name: /^Suppliers/ }).click()
  await expect(page.getByRole('cell', { name: /Green Valley Farms/ })).toBeVisible()
  await expect(page.getByRole('cell', { name: /Harborview Hotel Group/ })).toHaveCount(0)
})

test('AC-014-2: a counterparty shows its months, accounts, bank lines and documents like the mock', async ({ page }) => {
  await serve(page)
  await page.goto(`/preview/counterparties/${DETAIL.counterpartyId}`)
  await expect(page.getByRole('heading', { name: 'Roastline Equipment Service' })).toBeVisible()
  await expect(page.getByRole('cell', { name: '••••3108' })).toBeVisible()
  await expect(page.getByRole('link', { name: 'RES-0051' })).toBeVisible()
  await noOverflow(page)
  await expect(page).toHaveScreenshot('counterparty.png', { fullPage: true })
  await axeClean(page)
  const implementation = await detailOutline(page)
  await page.goto(mockUrl('counterparty'))
  expect(await detailOutline(page)).toEqual(implementation)
})
