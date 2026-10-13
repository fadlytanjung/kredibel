import { expect, type Page, test } from '@playwright/test'

// Synthetic queue (docs/18): a held copy, a proposal, an unpaid bill and a value to check.
const idr = (amount: string) => ({ amount, currency: 'IDR' })
const ITEMS = [
  { itemId: 'itm_0000000000000003', kind: 'POSSIBLE_DUPLICATE', month: '2026-03', status: 'OPEN', priority: 100, title: 'This statement covers days another statement already covers', subject: { docIds: ['doc_copy', 'doc_feb'] }, suggestion: {}, allowedActions: ['CONFIRM_DUPLICATE', 'NOT_DUPLICATE'] },
  { itemId: 'itm_0000000000000001', kind: 'PROPOSED_MATCH', month: '2026-02', status: 'OPEN', priority: 70, title: 'Confirm the payment of IDR 19,205,109.00 on 9 Feb 2026', subject: { bankLineIds: ['tx_9feb'], invoiceIds: ['inv_0010'], matchId: 'mat_feb' }, suggestion: { candidates: [{ matchId: 'mat_feb', invoiceIds: ['inv_0010'], score: '0.82', reasons: ['NET_OF_TAX', 'PARTY_MATCH', 'DATE_NEAR'] }] }, allowedActions: ['CONFIRM_MATCH', 'MATCH', 'REJECT_MATCH'] },
  { itemId: 'itm_0000000000000002', kind: 'UNMATCHED_DOCUMENT', month: '2026-02', status: 'OPEN', priority: 50, title: 'Invoice BW-0042 of IDR 990,000.00 is unpaid after its due date', subject: { invoiceIds: ['inv_bw42'], docIds: ['doc_bw42'] }, suggestion: {}, allowedActions: ['MATCH', 'NOT_YET_PAID', 'IGNORE'] },
  { itemId: 'itm_0000000000000004', kind: 'LOW_CONFIDENCE_VALUE', month: '2026-06', status: 'OPEN', priority: 40, title: 'Check the date and total read from the receipt of 17 Jun 2026', subject: { receiptIds: ['rcp_17jun'], docIds: ['doc_rcp'], field: 'total' }, suggestion: {}, allowedActions: ['CORRECT_VALUE', 'ACCEPT_AS_READ'] },
]
const LINES = [
  { txId: 'tx_9feb', docId: 'doc_feb', date: '2026-02-09', month: '2026-02', description: 'TRANSFER IN HIGHLAND CAFE', amount: idr('19205109.00'), support: 'PROPOSED', match: { state: 'PROPOSED' } },
  { txId: 'tx_21feb', docId: 'doc_feb', date: '2026-02-21', month: '2026-02', description: 'TRANSFER TO BLUEWATER TRADING', amount: idr('-990000.00'), support: 'NO_SUPPORT', match: { state: 'UNMATCHED' } },
]
const INVOICES = [
  { invoiceId: 'inv_0010', docId: 'doc_0010', kind: 'SALES', number: 'INV/SCR/2026/02/0010', buyerName: 'Highland Café', issueDate: '2026-02-02', month: '2026-02', total: idr('19597050.00') },
  { invoiceId: 'inv_bw42', docId: 'doc_bw42', kind: 'PURCHASE', number: 'BW-0042', issuerName: 'Bluewater Trading Co.', issueDate: '2026-02-03', month: '2026-02', total: idr('990000.00') },
]

async function serve(page: Page) {
  // Only the API: Vite serves modules such as /src/shared/api/client.ts too.
  await page.route((url) => url.pathname.startsWith('/api/'), (route) => {
    const url = route.request().url()
    const one = url.match(/\/api\/review-items\/(itm_\w+)$/)
    if (url.includes('/api/review-items?')) {
      const countsByKind = Object.fromEntries(ITEMS.map((i) => [i.kind, 1]))
      return route.fulfill({ json: { items: ITEMS, countsByKind, nextCursor: null } })
    }
    if (one) return route.fulfill({ json: ITEMS.find((i) => i.itemId === one[1]) })
    if (url.includes('/api/bank-lines')) return route.fulfill({ json: { items: LINES } })
    if (url.includes('/api/invoices')) return route.fulfill({ json: { items: INVOICES } })
    return route.fulfill({ json: { items: [] } })
  })
}

test.describe('Visual Regression: Review (spec 009, T009-06)', () => {
  test('the queue matches baseline', async ({ page }) => {
    await serve(page)
    await page.goto('/preview/review')
    await page.waitForSelector('text=Confirm the payment of IDR 19,205,109.00 on 9 Feb 2026')
    await expect(page).toHaveScreenshot('review-queue.png', { fullPage: true })
  })

  test('a proposal beside the queue matches baseline', async ({ page }) => {
    await serve(page)
    await page.goto('/preview/review/itm_0000000000000001')
    await page.waitForSelector('text=TRANSFER IN HIGHLAND CAFE')
    await expect(page).toHaveScreenshot('review-proposal.png', { fullPage: true })
  })
})
