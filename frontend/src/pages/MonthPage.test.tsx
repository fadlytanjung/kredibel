import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { apiClient } from '../shared/api/client'
import { MonthPage } from './MonthPage'

vi.mock('../shared/api/client', () => ({
  apiClient: vi.fn(),
  ProblemError: class ProblemError extends Error {},
}))

const fact = (name: string, value: string) => ({ factId: `fact:2026-03:${name}`, value, inputs: [] })

// Contract-shaped data (contracts/openapi.yaml Month, BankLine, Match), synthetic MYR workspace.
const MONTH = {
  month: '2026-03',
  state: 'NEEDS_REVIEW',
  figures: {
    opening: fact('opening', '2502.33'),
    moneyIn: fact('money_in', '4887.94'),
    moneyOut: fact('money_out', '5831.45'),
    closing: fact('closing', '1528.82'),
    bankLines: fact('bank_lines', '6'),
    excluded: fact('excluded', '1'),
    autoMatched: fact('auto_matched', '1'),
    manuallyMatched: fact('manually_matched', '1'),
    proposed: fact('proposed', '1'),
    unmatched: fact('unmatched', '2'),
    autoMatchRate: fact('auto_match_rate', '0.2000'),
  },
}

const line = (txId: string, description: string, amount: string, extra: Record<string, unknown>) => ({
  txId,
  docId: 'doc_1',
  page: 1,
  rowIndex: 0,
  date: '2026-03-11',
  month: '2026-03',
  description,
  amount: { amount, currency: 'MYR' },
  category: 'UNKNOWN',
  cashflowClass: 'UNCLASSIFIED',
  categorizedBy: 'MODEL',
  match: { state: 'UNMATCHED', matchIds: [] },
  ...extra,
})

const LINES = [
  line('tx_auto', 'TRANSFER IN DAYBREAK CAFE', '1500.00', {
    category: 'SALES_RECEIPT',
    cashflowClass: 'OPERATING',
    support: 'MATCHED',
    match: { state: 'AUTO', matchIds: ['mat_auto'] },
  }),
  line('tx_manual', 'TRANSFER OUT PRIMEPACK PACKAGING', '-320.00', {
    category: 'INVENTORY_PURCHASE',
    cashflowClass: 'OPERATING',
    support: 'MATCHED',
    match: { state: 'MANUAL', matchIds: ['mat_manual'] },
  }),
  line('tx_proposed', 'TRANSFER OUT GREEN VALLEY FARMS', '-985.00', {
    category: 'SUPPLIER_PAYMENT',
    cashflowClass: 'OPERATING',
    support: 'PROPOSED',
    match: { state: 'PROPOSED', matchIds: ['mat_proposed'] },
  }),
  line('tx_none', 'DEBIT CARD CENDANA FUEL', '-65.00', { support: 'NO_SUPPORT' }),
  line('tx_rent', 'STANDING ORDER RENT', '-2000.00', {
    category: 'RENT',
    cashflowClass: 'OPERATING',
    categorizedBy: 'USER',
    support: 'NOT_REQUIRED',
  }),
  line('tx_own', 'TRANSFER TO OWN SAVINGS', '-500.00', {
    category: 'INTERNAL_TRANSFER',
    cashflowClass: 'NON_CASH',
    support: 'EXCLUDED',
    match: { state: 'EXCLUDED', matchIds: [] },
  }),
]

const MATCHES = [
  { matchId: 'mat_auto', month: '2026-03', kind: 'BANK_SALES_INVOICE', method: 'AUTO', status: 'CONFIRMED', reasons: ['AMOUNT_EXACT', 'PARTY_MATCH'], amount: { amount: '1500.00', currency: 'MYR' } },
  { matchId: 'mat_manual', month: '2026-03', kind: 'BANK_PURCHASE_INVOICE', method: 'MANUAL', status: 'CONFIRMED', reasons: [], amount: { amount: '320.00', currency: 'MYR' } },
]

const INVOICES = [
  { invoiceId: 'inv_1', docId: 'doc_inv1', kind: 'SALES', number: 'INV/SCR/2026/03/0009', buyerName: 'Daybreak Café', issueDate: '2026-03-12', month: '2026-03', total: { amount: '1500.00', currency: 'MYR' }, evidence: { payment: 'PAID_BANK', printedCurrency: 'MYR' } },
  { invoiceId: 'inv_2', docId: 'doc_inv2', kind: 'PURCHASE', number: 'BW-0042', issuerName: 'Bluewater Trading Co.', issueDate: '2026-03-04', month: '2026-03', total: { amount: '800.00', currency: 'MYR' }, evidence: { payment: 'UNPAID', printedCurrency: 'MYR' } },
]
const RECEIPTS = [
  { receiptId: 'rcp_1', docId: 'doc_rcp1', merchantName: 'Cendana Fuel', date: '2026-03-18', month: '2026-03', total: { amount: '65.00', currency: 'MYR' }, evidence: { payment: 'PAID_CASH', printedCurrency: null } },
]
const FINDINGS = [
  { findingId: 'fnd_1', code: 'R02_SUPPLIER_INVOICE_UNKNOWN_PARTY', severity: 'MEDIUM', title: 'Invoice from a supplier never paid before', status: 'OPEN', month: '2026-03', facts: {}, evidence: [], nextSteps: ['Check who sent it.'] },
  { findingId: 'fnd_2', code: 'B01_GAMBLING_INDICATORS', severity: 'LOW', title: 'Old finding', status: 'RESOLVED', month: '2026-03', facts: {}, evidence: [] },
]

function serve(month: Record<string, unknown> = MONTH, lines = LINES) {
  vi.mocked(apiClient).mockImplementation((url: string, opts?: RequestInit) => {
    if (opts?.method === 'DELETE') return Promise.resolve({})
    if (url.startsWith('/api/invoices?month=2026-03')) return Promise.resolve({ items: INVOICES })
    if (url.startsWith('/api/receipts?month=2026-03')) return Promise.resolve({ items: RECEIPTS })
    if (url.startsWith('/api/findings?month=2026-03')) return Promise.resolve({ items: FINDINGS })
    if (url.startsWith('/api/months/2026-03')) return Promise.resolve(month)
    if (url.startsWith('/api/bank-lines?month=2026-03')) return Promise.resolve({ items: lines, nextCursor: null })
    if (url.startsWith('/api/matches?month=2026-03')) return Promise.resolve({ items: MATCHES })
    if (url.startsWith('/api/workspace')) return Promise.resolve({ orgId: 'org_1', currency: 'MYR' })
    return Promise.resolve({})
  })
}

describe('MonthPage', () => {
  let queryClient: QueryClient

  beforeEach(() => {
    queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    vi.clearAllMocks()
  })

  function Where() {
    const location = useLocation()
    return <span data-testid="where">{location.pathname + location.search}</span>
  }

  function renderPage(month = '2026-03', search = '') {
    return render(
      <MemoryRouter initialEntries={[`/months/${month}${search}`]}>
        <QueryClientProvider client={queryClient}>
          <Routes>
            <Route path="/months/:month" element={<><MonthPage /><Where /></>} />
            <Route path="/documents/:docId" element={<Where />} />
          </Routes>
        </QueryClientProvider>
      </MemoryRouter>,
    )
  }

  it('shows each figure once in the workspace currency, from the month run (AC-007-12)', async () => {
    serve()
    renderPage()

    const figures = await screen.findByRole('region', { name: /Figures/i })
    await waitFor(() => expect(within(figures).getByText('2,502.33')).toBeInTheDocument())
    expect(within(figures).getByText('4,887.94')).toBeInTheDocument()
    expect(within(figures).getByText('5,831.45')).toBeInTheDocument()
    expect(within(figures).getByText('1,528.82')).toBeInTheDocument()
    expect(figures.textContent).not.toMatch(/MYR\s*MYR/)
    // The real automatic match rate, and no ledger difference without a ledger.
    expect(within(figures).getByText('20%')).toBeInTheDocument()
    expect(within(figures).getByText('1 of 5 lines matched automatically')).toBeInTheDocument()
    expect(within(figures).getByText('No ledger imported yet')).toBeInTheDocument()
    expect(screen.getByText('Needs review')).toBeInTheDocument()
    expect(screen.queryByText('86%')).not.toBeInTheDocument()
  })

  it('says a figure is missing instead of inventing one', async () => {
    serve({ month: '2026-03', state: 'COLLECTING', figures: {} }, [])
    renderPage()

    const figures = await screen.findByRole('region', { name: /Figures/i })
    await waitFor(() => expect(screen.getByText('Collecting')).toBeInTheDocument())
    expect(within(figures).getAllByText('—')).toHaveLength(6)
    expect(within(figures).getAllByText('No printed balances this month')).toHaveLength(2)
    expect(screen.queryByRole('region', { name: /by match state/i })).not.toBeInTheDocument()
  })

  it('labels each kind of support and category differently (AC-007-12, ADR-025)', async () => {
    serve()
    renderPage()

    await waitFor(() => expect(screen.getByText('TRANSFER IN DAYBREAK CAFE')).toBeInTheDocument())
    const chip = (label: string) =>
      screen
        .getAllByText(label)
        .map((el) => el.closest('.match-chip'))
        .find(Boolean)
    expect(chip('Matched by Kredibel')).toHaveClass('auto')
    expect(chip('Matched by you')).toHaveClass('manual')
    expect(chip('Proposed match')).toHaveClass('proposed')
    expect(chip('No document yet')).toHaveClass('none')
    expect(chip('No document needed')).toHaveClass('cleared')
    expect(chip('Not counted')).toHaveClass('excluded')
    expect(screen.getByText('Same amount, Same party')).toBeInTheDocument()

    expect(screen.getByText('Sales receipts')).toHaveClass('badge-brand')
    expect(screen.getByText('Between own accounts')).toHaveClass('badge-outline')
    expect(screen.getByText('Not categorized yet')).toHaveClass('badge-medium')
    expect(screen.getByText('Rent')).toHaveClass('badge-brand')
    expect(screen.getByText('Set by you')).toBeInTheDocument()
  })

  it('unmatch calls the unmatch API (AC-007-13)', async () => {
    serve()
    renderPage()

    const row = (await screen.findByText('TRANSFER IN DAYBREAK CAFE')).closest('tr') as HTMLElement
    fireEvent.click(within(row).getByRole('button', { name: 'Unmatch' }))

    await waitFor(() =>
      expect(apiClient).toHaveBeenCalledWith('/api/matches/mat_auto', expect.objectContaining({ method: 'DELETE' })),
    )
  })

  it('opens MatchSheet when Match button is clicked on an unmatched line', async () => {
    serve()
    renderPage()

    const row = (await screen.findByText('DEBIT CARD CENDANA FUEL')).closest('tr') as HTMLElement
    fireEvent.click(within(row).getByRole('button', { name: 'Match' }))

    expect(await screen.findByRole('dialog')).toBeInTheDocument()
    expect(screen.getByText('Match bank transaction')).toBeInTheDocument()
  })

  it('searches bank lines by description and category', async () => {
    serve()
    renderPage()

    await waitFor(() => expect(screen.getByText('TRANSFER IN DAYBREAK CAFE')).toBeInTheDocument())
    const search = screen.getByRole('textbox', { name: /Search/i })
    fireEvent.change(search, { target: { value: 'DAYBREAK' } })
    expect(screen.getByText('TRANSFER IN DAYBREAK CAFE')).toBeInTheDocument()
    expect(screen.queryByText('TRANSFER OUT GREEN VALLEY FARMS')).not.toBeInTheDocument()

    fireEvent.change(search, { target: { value: 'rent' } })
    expect(screen.getByText('STANDING ORDER RENT')).toBeInTheDocument()
    expect(screen.queryByText('TRANSFER IN DAYBREAK CAFE')).not.toBeInTheDocument()
  })

  it("has the mock's tabs with counts, kept in the address (AC-007-12)", async () => {
    serve()
    renderPage()

    const tab = (name: RegExp) => screen.getByRole('tab', { name })
    await waitFor(() => expect(tab(/Documents/)).toHaveTextContent('3'))
    expect(tab(/Bank lines/)).toHaveAttribute('aria-selected', 'true')
    expect(tab(/Bank lines/)).toHaveTextContent('6')
    expect(tab(/Findings/)).toHaveTextContent('1')
    expect(tab(/Findings/).querySelector('.count')).toHaveClass('is-attn')

    fireEvent.click(tab(/Findings/))
    expect(screen.getByTestId('where')).toHaveTextContent('/months/2026-03?tab=findings')
    expect(screen.getByText('Invoice from a supplier never paid before')).toBeInTheDocument()
    expect(screen.queryByText('Old finding')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Medium/ })).toHaveTextContent('1')

    fireEvent.click(tab(/Ledger/))
    expect(screen.getByText(/Upload a general-ledger export/)).toBeInTheDocument()
  })

  it("lists the month's documents with their payment evidence, each opening its document", async () => {
    serve()
    renderPage('2026-03', '?tab=documents')

    await waitFor(() => expect(screen.getByText('Invoice INV/SCR/2026/03/0009')).toBeInTheDocument())
    const chip = (label: string) => screen.getByText(label).closest('.match-chip')
    expect(chip('Paid through the bank')).toHaveClass('auto')
    expect(chip('Unpaid after its due date')).toHaveClass('overdue')
    expect(chip('Paid in cash')).toHaveClass('cleared')
    expect(screen.getByText('Sales, to Daybreak Café')).toBeInTheDocument()
    expect(screen.getByText('Purchase, from Bluewater Trading Co.')).toBeInTheDocument()
    // The receipt prints no currency: read in the workspace currency, and it says so (ADR-025).
    expect(screen.getAllByText('No currency printed: read as MYR')).toHaveLength(1)

    fireEvent.click(screen.getByText('Receipt'))
    expect(screen.getByTestId('where')).toHaveTextContent('/documents/doc_rcp1')
  })

  it('says a month without data is empty and opens the latest month that has data', async () => {
    vi.mocked(apiClient).mockImplementation((url: string) => {
      if (url === '/api/months') {
        return Promise.resolve({ items: [{ month: '2026-06', state: 'RECONCILED', figures: { bankLines: fact('bank_lines', '26') } }] })
      }
      if (url.startsWith('/api/months/2026-10')) return Promise.reject(new Error('not found'))
      if (url.startsWith('/api/workspace')) return Promise.resolve({ orgId: 'org_1', currency: 'IDR' })
      return Promise.resolve({ items: [] })
    })
    renderPage('2026-10')

    expect(await screen.findByText('Nothing for October 2026 yet')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Open June 2026' })).toHaveAttribute('href', '/months/2026-06')
    expect(screen.queryByRole('tab', { name: /Bank lines/ })).not.toBeInTheDocument()
  })

  it("shows the explainer's finding citations as chips that open the evidence (AC-008-6)", async () => {
    serve({
      ...MONTH,
      risk: {
        level: 'HIGH',
        summary: 'An invoice came from a supplier never paid before [[finding:fnd_1]]; the month is otherwise balanced [[fact:2026-03:closing]].',
        nextSteps: ['Check who sent it.'],
        reasons: ['fnd_1'],
        grounding: { verdict: 'AGREED', citations: ['finding:fnd_1'] },
      },
    })
    renderPage()

    expect(await screen.findByText('High risk this month')).toBeInTheDocument()
    const chip = screen.getByRole('link', { name: 'R02' })
    expect(chip).toHaveAttribute('href', '/risk/fnd_1')
    const lead = chip.closest('p')
    expect(lead).toHaveTextContent('An invoice came from a supplier never paid before R02; the month is otherwise balanced.')
    expect(lead?.textContent).not.toContain('[[')
  })
})
