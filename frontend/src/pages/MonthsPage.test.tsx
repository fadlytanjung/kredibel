import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { apiClient } from '../shared/api/client'
import { MonthsPage } from './MonthsPage'

vi.mock('../shared/api/client', () => ({
  apiClient: vi.fn(),
  ProblemError: class ProblemError extends Error {},
}))

describe('MonthsPage', () => {
  let queryClient: QueryClient

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })
    vi.clearAllMocks()
  })

  function renderPage() {
    return render(
      <MemoryRouter initialEntries={['/months/all']}>
        <QueryClientProvider client={queryClient}>
          <Routes>
            <Route path="/months/all" element={<MonthsPage />} />
            <Route path="/months/:month" element={<p>Month page</p>} />
          </Routes>
        </QueryClientProvider>
      </MemoryRouter>,
    )
  }

  it('renders reconciliation header and empty state when no months exist', async () => {
    vi.mocked(apiClient).mockImplementation((url: string) => {
      if (url.includes('/api/months')) {
        return Promise.resolve({ items: [] })
      }
      if (url.includes('/api/workspace')) {
        return Promise.resolve({ orgId: 'org_1', currency: 'IDR' })
      }
      return Promise.resolve({})
    })

    renderPage()

    expect(screen.getByText('Reconciliation')).toBeInTheDocument()
    await waitFor(() => {
      expect(
        screen.getByText('No reconciled months yet. Upload your first bank statement or invoice to begin.'),
      ).toBeInTheDocument()
    })
  })

  it('lists every month, newest first, each opening its page, and shows no sample rows', async () => {
    vi.mocked(apiClient).mockImplementation((url: string) => {
      if (url.includes('/api/months')) {
        return Promise.resolve({
          items: [
            { month: '2026-01', state: 'RECONCILED', statements: [{ docId: 'd1' }], figures: {} },
            { month: '2026-03', state: 'NEEDS_REVIEW', statements: [{ docId: 'd3' }], figures: {} },
          ],
        })
      }
      if (url.includes('/api/workspace')) return Promise.resolve({ orgId: 'org_1', currency: 'IDR' })
      return Promise.resolve({})
    })

    renderPage()

    await waitFor(() => expect(screen.getByText('March 2026')).toBeInTheDocument())
    const rows = screen.getAllByRole('row').slice(1)
    expect(rows[0]).toHaveTextContent('March 2026')
    expect(rows[0]).toHaveTextContent('Needs review')
    expect(rows[1]).toHaveTextContent('January 2026')
    expect(rows[1]).toHaveTextContent('Reconciled')
    expect(screen.queryByText('Daybreak Café')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Bank evidence' })).toHaveAttribute('aria-pressed', 'false')
    expect(screen.getByRole('button', { name: /Needs review/ })).toHaveTextContent('1')
    fireEvent.change(screen.getByRole('textbox', { name: /Search/i }), { target: { value: 'january' } })
    expect(screen.queryByText('March 2026')).not.toBeInTheDocument()
    fireEvent.click(screen.getByText('January 2026'))
    expect(screen.getByText('Month page')).toBeInTheDocument()
  })

  it('shows bank evidence, documents first and currency on the served books (T007-10c)', async () => {
    const calls: string[] = []
    vi.mocked(apiClient).mockImplementation((url: string) => {
      calls.push(url)
      if (url.startsWith('/api/months')) return Promise.resolve({ items: [{ month: '2026-03', state: 'NEEDS_REVIEW', statements: [], figures: {} }] })
      if (url.startsWith('/api/workspace')) return Promise.resolve({ orgId: 'org_1', currency: 'IDR' })
      if (url.startsWith('/api/bank-lines'))
        return Promise.resolve({
          items: [
            { txId: 'tx_fee', docId: 'd3', month: '2026-03', date: '2026-03-31', description: 'ADMIN FEE', amount: { amount: '-25000.00', currency: 'IDR' }, support: 'NO_SUPPORT', match: { state: 'UNMATCHED', matchIds: [] } },
          ],
        })
      if (url.startsWith('/api/invoices'))
        return Promise.resolve({
          items: [
            { invoiceId: 'inv_1', docId: 'doc_1', kind: 'PURCHASE', number: 'PP-201', issuerName: 'Primepack Packaging', issueDate: '2026-03-12', month: '2026-03', total: { amount: '450000.00', currency: 'IDR' }, evidence: { payment: 'WAITING_FOR_STATEMENT', printedCurrency: 'IDR', covered: false, approved: false } },
            { invoiceId: 'inv_2', docId: 'doc_2', kind: 'PURCHASE', number: 'RL-0402', issuerName: 'Roastline', issueDate: '2026-04-02', month: '2026-04', total: { amount: '1500.00', currency: 'USD' }, evidence: { payment: 'CURRENCY_TO_CONFIRM', printedCurrency: 'USD', covered: false, approved: false } },
          ],
        })
      if (url.startsWith('/api/receipts')) return Promise.resolve({ items: [] })
      return Promise.resolve({})
    })

    renderPage()
    await waitFor(() => expect(screen.getByText('March 2026')).toBeInTheDocument())
    expect(calls.some((c) => c.startsWith('/api/bank-lines'))).toBe(false)

    fireEvent.click(screen.getByRole('button', { name: 'Bank evidence' }))
    await waitFor(() => expect(screen.getByText('ADMIN FEE')).toBeInTheDocument())
    expect(screen.getAllByText('No document yet').length).toBeGreaterThanOrEqual(2) // the chip and the row
    expect(screen.getByText('Bank cash is recorded. Upload its invoice or receipt, or say it needs none.')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Documents first' }))
    await waitFor(() => expect(screen.getByText('Invoice PP-201')).toBeInTheDocument())
    expect(screen.getAllByText('Waiting for the statement').length).toBeGreaterThanOrEqual(2)
    expect(screen.getAllByRole('button', { name: 'Approve document' }).length).toBeGreaterThan(0)
    fireEvent.click(screen.getAllByRole('button', { name: 'Confirm payment' })[0])
    expect(screen.getByRole('dialog', { name: 'Confirm payment manually' })).toBeInTheDocument()
    expect(screen.getByLabelText('Amount paid, IDR')).toHaveValue(450000)

    fireEvent.click(screen.getByRole('button', { name: 'Currency' }))
    await waitFor(() => expect(screen.getByText('Invoice RL-0402')).toBeInTheDocument())
    expect(screen.getByText('The document says USD 1,500.00. Use its amounts as IDR 1,500.00 without conversion?')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Use amounts as IDR' })).toBeInTheDocument()
  })
})
