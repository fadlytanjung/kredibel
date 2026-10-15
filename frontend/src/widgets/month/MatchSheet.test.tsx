import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import type { BankLine } from '../../entities/bank-line'
import type { Row } from './useMonthDocuments'
import { MatchSheet } from './MatchSheet'
import { apiClient } from '../../shared/api/client'

vi.mock('../../shared/api/client', () => ({
  apiClient: vi.fn(),
}))

const LINE_OUT: BankLine = {
  txId: 'tx_rent',
  docId: 'doc_stmt',
  date: '2026-06-01',
  description: 'WAREHOUSE RENT JUN',
  amount: { amount: '-15000000.00', currency: 'IDR' },
  month: '2026-06',
  support: 'NO_SUPPORT',
  match: { state: 'UNMATCHED', matchIds: [] },
}

const LINE_IN: BankLine = {
  txId: 'tx_hotel',
  docId: 'doc_stmt',
  date: '2026-06-05',
  description: 'PAYMENT HARBORVIEW',
  amount: { amount: '45000000.00', currency: 'IDR' },
  month: '2026-06',
  support: 'NO_SUPPORT',
  match: { state: 'UNMATCHED', matchIds: [] },
}

const DOCUMENTS: Row[] = [
  {
    id: 'inv_rent',
    docId: 'doc_inv_rent',
    kind: 'PURCHASE',
    number: 'INV-RENT-06',
    party: 'Dago Industrial Estate',
    date: '2026-06-01',
    total: { amount: '15000000.00', currency: 'IDR' },
    payment: 'UNPAID',
    noCurrencyPrinted: false,
  },
  {
    id: 'rcp_fuel',
    docId: 'doc_rcp_fuel',
    kind: 'RECEIPT',
    number: 'RCP-8891',
    party: 'Pertamina Dago',
    date: '2026-06-02',
    total: { amount: '250000.00', currency: 'IDR' },
    payment: 'PAID_CASH',
    noCurrencyPrinted: false,
  },
  {
    id: 'inv_sales_hotel',
    docId: 'doc_inv_hotel',
    kind: 'SALES',
    number: 'INV-SLS-01',
    party: 'Harborview Hotel Group',
    date: '2026-06-04',
    total: { amount: '45000000.00', currency: 'IDR' },
    payment: 'UNPAID',
    noCurrencyPrinted: false,
  },
]

describe('MatchSheet', () => {
  let queryClient: QueryClient

  beforeEach(() => {
    queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    vi.clearAllMocks()
  })

  function renderSheet(props: Partial<React.ComponentProps<typeof MatchSheet>> = {}) {
    return render(
      <QueryClientProvider client={queryClient}>
        <MatchSheet
          line={LINE_OUT}
          month="2026-06"
          currency="IDR"
          documents={DOCUMENTS}
          onClose={vi.fn()}
          {...props}
        />
      </QueryClientProvider>,
    )
  }

  it('renders transaction details and exact amount match candidate', () => {
    renderSheet()

    expect(screen.getByText('WAREHOUSE RENT JUN')).toBeInTheDocument()
    expect(screen.getAllByText(/15,000,000/).length).toBeGreaterThanOrEqual(1)
    // Purchase candidate shown
    const candidate = screen.getAllByRole('radio')[0]
    expect(candidate).toHaveTextContent('INV-RENT-06')
    expect(screen.getAllByText(/Dago Industrial Estate/).length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText('Exact amount')).toBeInTheDocument()
    // Sales invoice should not appear in candidates for outgoing transaction
    expect(screen.queryByText(/Harborview Hotel Group/)).not.toBeInTheDocument()
  })

  it('links matching candidate to bank line via API', async () => {
    vi.mocked(apiClient).mockResolvedValueOnce({ matchId: 'mat_new' })
    const onMatched = vi.fn()
    const onClose = vi.fn()
    renderSheet({ onMatched, onClose })

    // Click candidate
    fireEvent.click(screen.getAllByRole('radio')[0])
    // Click link button
    const linkBtn = screen.getByRole('button', { name: /Link document/i })
    expect(linkBtn).not.toBeDisabled()
    fireEvent.click(linkBtn)

    await waitFor(() =>
      expect(apiClient).toHaveBeenCalledWith(
        '/api/matches',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            bankLineIds: ['tx_rent'],
            invoiceIds: ['inv_rent'],
          }),
        }),
      ),
    )
    expect(onMatched).toHaveBeenCalledWith('INV-RENT-06')
    expect(onClose).toHaveBeenCalled()
  })

  it('records SUPPORT_NOT_REQUIRED decision when user says no document needed', async () => {
    vi.mocked(apiClient).mockResolvedValueOnce({ decisionId: 'dec_1' })
    const onNotRequired = vi.fn()
    const onClose = vi.fn()
    renderSheet({ onNotRequired, onClose })

    const noDocBtn = screen.getByRole('button', { name: /No document needed/i })
    fireEvent.click(noDocBtn)

    await waitFor(() =>
      expect(apiClient).toHaveBeenCalledWith(
        '/api/decisions',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            kind: 'SUPPORT_NOT_REQUIRED',
            txId: 'tx_rent',
            reason: 'No supporting document is needed for this line.',
          }),
        }),
      ),
    )
    expect(onNotRequired).toHaveBeenCalled()
    expect(onClose).toHaveBeenCalled()
  })

  it('filters candidates for sales invoices on incoming transactions', () => {
    renderSheet({ line: LINE_IN })

    expect(screen.getByText('PAYMENT HARBORVIEW')).toBeInTheDocument()
    const candidate = screen.getByRole('radio')
    expect(candidate).toHaveTextContent('INV-SLS-01')
    expect(candidate).toHaveTextContent('Harborview Hotel Group')
    // Outgoing documents should not appear in candidate
    expect(candidate).not.toHaveTextContent('INV-RENT-06')
  })

  it('renders AI match suggestion card and allows selecting recommended document', async () => {
    vi.mocked(apiClient).mockImplementation(async (url: string) => {
      if (url.includes('/api/bank-lines/tx_rent/ai-suggestion')) {
        return {
          recommendedDocId: 'inv_rent',
          confidence: 0.95,
          reason: 'Matches warehouse lease payment for June 2026',
          missingDocumentAdvice: '',
        }
      }
      return null
    })

    renderSheet()

    await waitFor(() => {
      expect(screen.getByText('AI Match Analysis')).toBeInTheDocument()
    })
    expect(screen.getByText(/95% Confidence/)).toBeInTheDocument()
    expect(screen.getByText('Matches warehouse lease payment for June 2026')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Select recommended document/i })).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /Select recommended document/i }))
    const candidate = screen.getAllByRole('radio')[0]
    expect(candidate).toHaveAttribute('aria-checked', 'true')
  })
})
