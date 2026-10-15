/**
 * The public site's product screenshots (spec 020, T020-31): the real app on its synthetic preview
 * routes, fed the same fixtures as the parity checks (spec 019), so the landing and How it works
 * always show the current screens. Synthetic data only (docs/18). Run: `npm run marketing:shots`.
 */
import { expect, type Page, test } from '@playwright/test'
import { DASHBOARD } from '../../src/widgets/dashboard/dashboard.fixture'
import { CASH, FLOW_PARTIES, FLOW_STATEMENT, LINES } from '../../src/widgets/dashboard/charts.fixture'
import { PNL } from '../../src/widgets/profit-loss/fixture'
import { DOCUMENT, MONTH, pageImageFromMock, REVIEW, WORKSPACE } from '../visual/fixtures'

const OUT = 'public/marketing'

/** One API for every screen: each route answers from its fixture, anything else is empty. */
async function serve(page: Page, extra: (path: string) => unknown = () => undefined, png?: Buffer) {
  const countsByKind = Object.fromEntries(
    REVIEW.items.map((i) => [i.kind, REVIEW.items.filter((o) => o.kind === i.kind).length]),
  )
  await page.route(
    (url) => url.pathname.startsWith('/api/'),
    (route) => {
      const url = new URL(route.request().url())
      const path = url.pathname
      const own = extra(path)
      if (own !== undefined) return route.fulfill({ json: own })
      if (path.includes('/pages/') && png) return route.fulfill({ body: png, contentType: 'image/png' })
      if (path === '/api/workspace') return route.fulfill({ json: WORKSPACE })
      if (path === '/api/dashboard') return route.fulfill({ json: DASHBOARD })
      if (path === '/api/profit-loss') return route.fulfill({ json: PNL })
      if (path === '/api/money-flow')
        return route.fulfill({ json: url.searchParams.get('view') === 'COUNTERPARTIES' ? FLOW_PARTIES : FLOW_STATEMENT })
      if (path === '/api/cash-flow') return route.fulfill({ json: CASH })
      if (path === '/api/review-items') return route.fulfill({ json: { items: REVIEW.items, countsByKind, nextCursor: null } })
      if (path === '/api/months/2026-03') return route.fulfill({ json: MONTH.month })
      if (path === '/api/months') return route.fulfill({ json: { items: MONTH.months } })
      if (path === '/api/matches') return route.fulfill({ json: { items: MONTH.matches } })
      if (path === '/api/invoices') return route.fulfill({ json: { items: MONTH.invoices } })
      if (path === '/api/receipts') return route.fulfill({ json: { items: MONTH.receipts } })
      if (path === '/api/findings') return route.fulfill({ json: { items: MONTH.findings } })
      if (path === '/api/bank-lines') return route.fulfill({ json: LINES })
      return route.fulfill({ json: { items: [] } })
    },
  )
}

async function shoot(page: Page, name: string) {
  await page.evaluate(() => document.fonts.ready)
  await page.screenshot({ path: `${OUT}/${name}.png`, animations: 'disabled' })
}

test('dashboard: the figures and where the money went', async ({ page }) => {
  await serve(page)
  await page.goto('/preview/shell')
  await page.getByRole('button', { name: 'All months', exact: true }).click()
  const panel = page.getByRole('heading', { name: 'Profit and loss', exact: true }).first()
  await expect(panel).toBeVisible()
  // Frame the profit and loss flow: the section is "where the money went".
  const top = (await panel.boundingBox())?.y ?? 0
  await page.evaluate((y) => window.scrollTo(0, y), Math.max(0, top - 120))
  await page.waitForTimeout(400)
  await shoot(page, 'dashboard')
})

test('month: March with its explained risk and bank lines', async ({ page }) => {
  await serve(page, (path) => (path === '/api/bank-lines' ? { items: MONTH.lines, nextCursor: null } : undefined))
  await page.goto('/preview/months/2026-03')
  await expect(page.getByRole('heading', { name: 'March 2026' })).toBeVisible()
  await expect(page.getByText('Critical risk this month')).toBeVisible()
  await shoot(page, 'month')
})

test('review: the short queue', async ({ page }) => {
  await serve(page, (path) => (path === '/api/bank-lines' ? { items: REVIEW.lines, nextCursor: null } : undefined))
  await page.goto('/preview/review')
  await expect(page.getByText('Confirm the payment of IDR 18,700,000 on 9 Feb 2026')).toBeVisible()
  await shoot(page, 'review')
})

test('evidence: the lamp on the printed value beside both readings', async ({ page }) => {
  const { png, box } = await pageImageFromMock(page, 'document')
  const lines = DOCUMENT.lines.map((line) =>
    line.txId === 'tx_feb_09' && box ? { ...line, readings: { amount: { ...line.readings.amount, bbox: box } } } : line,
  )
  await serve(
    page,
    (path) => {
      if (path === `/api/documents/${DOCUMENT.document.docId}`) return DOCUMENT.document
      if (path === '/api/bank-lines') return { items: lines, nextCursor: null }
      return undefined
    },
    png,
  )
  await page.goto(`/preview/documents/${DOCUMENT.document.docId}`)
  await expect(page.getByRole('heading', { name: 'ACB_Feb_2026.pdf' })).toBeVisible()
  await page.getByRole('row', { name: /TRANSFER IN DAYBREAK CAFE/ }).click()
  await expect(page.locator('.page-zoom img')).toBeVisible()
  await page.evaluate(() => window.scrollTo(0, 0))
  await shoot(page, 'evidence-viewer')
})
