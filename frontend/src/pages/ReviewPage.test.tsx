import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { apiClient } from '../shared/api/client'
import { ReviewPage } from './ReviewPage'

vi.mock('../shared/api/client', () => ({
  apiClient: vi.fn(),
  ProblemError: class ProblemError extends Error {},
}))

const idr = (amount: string) => ({ amount, currency: 'IDR' })

// Contract-shaped (contracts/openapi.yaml ReviewItem), synthetic workspace.
const PROPOSAL = {
  itemId: 'itm_0000000000000001',
  kind: 'PROPOSED_MATCH',
  month: '2026-02',
  status: 'OPEN',
  priority: 70,
  title: 'Confirm the payment of IDR 19,205,109.00 on 9 Feb 2026',
  subject: { bankLineIds: ['tx_9feb'], invoiceIds: ['inv_0010'], matchId: 'mat_feb' },
  suggestion: { candidates: [{ matchId: 'mat_feb', invoiceIds: ['inv_0010'], score: '0.82', reasons: ['NET_OF_TAX', 'PARTY_MATCH'] }] },
  allowedActions: ['CONFIRM_MATCH', 'MATCH', 'REJECT_MATCH'],
}
const UNPAID = {
  itemId: 'itm_0000000000000002',
  kind: 'UNMATCHED_DOCUMENT',
  month: '2026-02',
  status: 'OPEN',
  priority: 50,
  title: 'Invoice BW-0042 of IDR 990,000.00 is unpaid after its due date',
  subject: { invoiceIds: ['inv_bw42'], docIds: ['doc_bw42'] },
  suggestion: {},
  allowedActions: ['MATCH', 'NOT_YET_PAID', 'IGNORE'],
}
const COPY = {
  itemId: 'itm_0000000000000003',
  kind: 'POSSIBLE_DUPLICATE',
  month: '2026-03',
  status: 'OPEN',
  priority: 100,
  title: 'This statement covers days another statement already covers',
  subject: { docIds: ['doc_copy', 'doc_orig'] },
  suggestion: {},
  allowedActions: ['CONFIRM_DUPLICATE', 'NOT_DUPLICATE'],
}
const LINES = [
  { txId: 'tx_9feb', docId: 'doc_feb', date: '2026-02-09', month: '2026-02', description: 'TRANSFER IN HIGHLAND CAFE', amount: idr('19205109.00'), support: 'PROPOSED', match: { state: 'PROPOSED' } },
  { txId: 'tx_21feb', docId: 'doc_feb', date: '2026-02-21', month: '2026-02', description: 'TRANSFER TO BLUEWATER TRADING', amount: idr('-990000.00'), support: 'NO_SUPPORT', match: { state: 'UNMATCHED' } },
  { txId: 'tx_25feb', docId: 'doc_feb', date: '2026-02-25', month: '2026-02', description: 'CARD PURCHASE', amount: idr('-120000.00'), support: 'NO_SUPPORT', match: { state: 'UNMATCHED' } },
]
const INVOICES = [
  { invoiceId: 'inv_0010', docId: 'doc_0010', kind: 'SALES', number: 'INV/SCR/2026/02/0010', buyerName: 'Highland Café', issueDate: '2026-02-02', month: '2026-02', total: idr('19597050.00') },
  { invoiceId: 'inv_bw42', docId: 'doc_bw42', kind: 'PURCHASE', number: 'BW-0042', issuerName: 'Bluewater Trading Co.', issueDate: '2026-02-03', month: '2026-02', total: idr('990000.00') },
]

const RECEIPTS = [
  { receiptId: 'rcp_17feb', docId: 'doc_rcp', merchantName: 'Cendana Fuel', date: '2026-02-17', month: '2026-02', total: idr('467976.00') },
]

function serve(items = [COPY, PROPOSAL, UNPAID]) {
  vi.mocked(apiClient).mockImplementation((url: string, init?: RequestInit) => {
    if (url.startsWith('/api/review-items?')) {
      const counts: Record<string, number> = {}
      for (const i of items) counts[i.kind] = (counts[i.kind] ?? 0) + 1
      return Promise.resolve({ items, countsByKind: counts, nextCursor: null })
    }
    const resolve = url.match(/^\/api\/review-items\/(itm_\w+)\/resolve$/)
    if (resolve) {
      const item = items.find((i) => i.itemId === resolve[1])
      const body = JSON.parse(String(init?.body)) as { action: string }
      return Promise.resolve({ ...item, status: 'RESOLVED', resolution: { action: body.action, resolvedBy: 'u-1' } })
    }
    const one = url.match(/^\/api\/review-items\/(itm_\w+)$/)
    if (one) return Promise.resolve(items.find((i) => i.itemId === one[1]))
    if (url.startsWith('/api/bank-lines?month=')) return Promise.resolve({ items: LINES })
    if (url.startsWith('/api/invoices?month=')) return Promise.resolve({ items: INVOICES })
    if (url.startsWith('/api/receipts?month=')) return Promise.resolve({ items: RECEIPTS })
    if (url.startsWith('/api/documents/')) return Promise.resolve({ docId: url.split('/').pop(), fileName: 'statement-2026-03.pdf' })
    return Promise.resolve({})
  })
}

function Where() {
  return <span data-testid="where">{useLocation().pathname}</span>
}

describe('ReviewPage', () => {
  let queryClient: QueryClient

  beforeEach(() => {
    queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    vi.clearAllMocks()
  })

  function renderAt(path: string) {
    return render(
      <MemoryRouter initialEntries={[path]}>
        <QueryClientProvider client={queryClient}>
          <Routes>
            <Route path="/review" element={<ReviewPage />} />
            <Route path="/review/:itemId" element={<ReviewPage />} />
          </Routes>
          <Where />
        </QueryClientProvider>
      </MemoryRouter>,
    )
  }

  it('lists the open items with a chip and count per kind, each opening its fix (AC-009-2)', async () => {
    serve()
    renderAt('/review')

    expect(await screen.findByText('Confirm the payment of IDR 19,205,109.00 on 9 Feb 2026')).toBeInTheDocument()
    const chips = screen.getByRole('group', { name: 'Kinds of items' })
    expect(within(chips).getByRole('button', { name: /Possible copies\s*1/ })).toBeInTheDocument()
    expect(within(chips).getByRole('button', { name: /Not paid\s*1/ })).toBeInTheDocument()

    fireEvent.click(within(chips).getByRole('button', { name: /Not paid/ }))
    expect(screen.queryByText('This statement covers days another statement already covers')).not.toBeInTheDocument()

    fireEvent.click(screen.getByText('Invoice BW-0042 of IDR 990,000.00 is unpaid after its due date'))
    await waitFor(() => expect(screen.getByTestId('where')).toHaveTextContent(`/review/${UNPAID.itemId}`))
  })

  it('shows a proposal with its reasons and fit, and confirming opens the next item (AC-009-4, AC-009-7)', async () => {
    serve()
    renderAt(`/review/${PROPOSAL.itemId}`)

    const panel = await screen.findByRole('region', { name: PROPOSAL.title })
    expect(within(panel).getByText('Choose a match')).toBeInTheDocument()
    expect(await within(panel).findByText('TRANSFER IN HIGHLAND CAFE')).toBeInTheDocument()
    expect(within(panel).getByText('Invoice INV/SCR/2026/02/0010')).toBeInTheDocument()
    expect(within(panel).getByText('Amount net of tax')).toBeInTheDocument()
    expect(within(panel).getByText('0.82')).toBeInTheDocument()
    expect(within(panel).getByRole('button', { name: 'Not this match' })).toBeInTheDocument()
    expect(within(panel).queryByRole('button', { name: 'It is a copy' })).not.toBeInTheDocument()

    fireEvent.click(within(panel).getByRole('button', { name: 'Confirm the match' }))

    await waitFor(() =>
      expect(apiClient).toHaveBeenCalledWith(
        `/api/review-items/${PROPOSAL.itemId}/resolve`,
        expect.objectContaining({ method: 'POST', body: JSON.stringify({ action: 'CONFIRM_MATCH', matchId: 'mat_feb' }) }),
      ),
    )
    expect(await screen.findByRole('status')).toHaveTextContent('Saved. February is being reconciled again. Next: 2 left')
    // Navigation is a transition: it may land a render after the status.
    await waitFor(() => expect(screen.getByTestId('where')).toHaveTextContent(`/review/${UNPAID.itemId}`))
  })

  it('offers the bank lines that could pay an unpaid bill, and leaving it needs a reason (AC-009-5)', async () => {
    serve()
    renderAt(`/review/${UNPAID.itemId}`)

    const panel = await screen.findByRole('region', { name: UNPAID.title })
    const lines = await within(panel).findByRole('radiogroup', { name: 'Bank lines that could be its payment' })
    expect(within(lines).getAllByRole('radio')).toHaveLength(1) // only the close amount, paid out
    expect(within(lines).getByText('TRANSFER TO BLUEWATER TRADING')).toBeInTheDocument()

    fireEvent.click(within(panel).getByRole('button', { name: 'Leave it, with a reason' }))
    const leave = within(panel).getByRole('button', { name: 'Leave it' })
    expect(leave).toBeDisabled()
    fireEvent.change(within(panel).getByLabelText('Why can it be left as it is?'), { target: { value: 'Paid in cash at the market' } })
    expect(leave).toBeEnabled()

    fireEvent.click(within(panel).getByRole('button', { name: 'Match with the line of 21 Feb 2026' }))
    await waitFor(() =>
      expect(apiClient).toHaveBeenCalledWith(
        `/api/review-items/${UNPAID.itemId}/resolve`,
        expect.objectContaining({ body: JSON.stringify({ action: 'MATCH', bankLineIds: ['tx_21feb'] }) }),
      ),
    )
  })

  it('corrects a value read from a receipt, as printed (AC-009-5, T009-03a)', async () => {
    const check = {
      itemId: 'itm_0000000000000004',
      kind: 'LOW_CONFIDENCE_VALUE',
      month: '2026-02',
      status: 'OPEN',
      priority: 40,
      title: 'Check the total read from the receipt of 17 Feb 2026',
      subject: { receiptIds: ['rcp_17feb'], docIds: ['doc_rcp'], field: 'total' },
      suggestion: {},
      allowedActions: ['CORRECT_VALUE', 'ACCEPT_AS_READ'],
    }
    serve([check])
    renderAt(`/review/${check.itemId}`)

    const panel = await screen.findByRole('region', { name: check.title })
    expect(await within(panel).findByText('Cendana Fuel, 17 Feb 2026')).toBeInTheDocument()
    fireEvent.click(within(panel).getByRole('button', { name: 'Correct it' }))
    fireEvent.change(within(panel).getByLabelText('The total as printed'), { target: { value: '476976.00' } })
    fireEvent.click(within(panel).getByRole('button', { name: 'Save the correction' }))

    await waitFor(() =>
      expect(apiClient).toHaveBeenCalledWith(
        `/api/review-items/${check.itemId}/resolve`,
        expect.objectContaining({ body: JSON.stringify({ action: 'CORRECT_VALUE', field: 'total', value: '476976.00' }) }),
      ),
    )
  })

  it('moves with J and K and closes with Esc (AC-009-7)', async () => {
    serve()
    renderAt(`/review/${COPY.itemId}`)

    await screen.findByRole('region', { name: COPY.title })
    fireEvent.keyDown(document, { key: 'j' })
    await waitFor(() => expect(screen.getByTestId('where')).toHaveTextContent(`/review/${PROPOSAL.itemId}`))
    fireEvent.keyDown(document, { key: 'k' })
    await waitFor(() => expect(screen.getByTestId('where')).toHaveTextContent(`/review/${COPY.itemId}`))
    fireEvent.keyDown(document, { key: 'Escape' })
    await waitFor(() => expect(screen.getByTestId('where')).toHaveTextContent(/^\/review$/))
  })
})
