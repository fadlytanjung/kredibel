import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { apiClient } from '../shared/api/client'
import { DashboardPage } from './DashboardPage'

vi.mock('../shared/api/client', () => ({
  apiClient: vi.fn(),
  ProblemError: class ProblemError extends Error {},
}))

const money = (amount: string) => ({ amount, currency: 'MYR' })

// Contract-shaped (contracts/openapi.yaml Dashboard), synthetic MYR workspace.
const DASHBOARD = {
  period: 'recent',
  periodMonths: ['2026-07', '2026-08', '2026-09'],
  kpis: [
    { id: 'MONEY_IN', value: money('4887.94'), previous: money('4100.00') },
    { id: 'MONEY_OUT', value: money('5831.45'), previous: null },
    { id: 'NET', value: money('-943.51'), previous: null },
    { id: 'AUTO_MATCH_RATE', value: '0.8960', previous: null },
    { id: 'OPEN_REVIEW_ITEMS', value: 3, previous: null },
    { id: 'DOCUMENTS_WAITING', value: 2, previous: null },
  ],
  months: [
    { month: '2026-07', state: 'RECONCILED', statementsPresent: 1, statementsExpected: 1, autoMatchRate: '0.9400', riskLevel: 'LOW' },
    { month: '2026-08', state: 'NEEDS_REVIEW', statementsPresent: 1, statementsExpected: 1, autoMatchRate: '0.8600', riskLevel: 'CRITICAL' },
    { month: '2026-09', state: 'COLLECTING', statementsPresent: 0, statementsExpected: 1 },
  ],
  alerts: [
    { severity: 'CRITICAL', title: 'The statement was edited after the bank issued it', month: '2026-08', findingId: 'fnd_1', link: '/risk/fnd_1' },
    { severity: 'MEDIUM', title: 'Invoices from an unknown supplier', month: '2026-09', findingId: 'fnd_2', link: '/risk/fnd_2' },
  ],
  reviewPreview: [
    {
      itemId: 'itm_0000000000000001',
      kind: 'PROPOSED_MATCH',
      month: '2026-08',
      status: 'OPEN',
      priority: 85,
      title: 'Confirm the payment of MYR 1,800.00 on 9 Aug 2026',
      subject: { matchId: 'mat_1' },
      allowedActions: ['CONFIRM_MATCH', 'MATCH', 'REJECT_MATCH'],
    },
  ],
  moneyFlowSummary: {
    topSources: [{ id: 'src:client:cp_1', column: 'SOURCE', label: 'Daybreak Cafe', value: money('2500.00') }],
    topUses: [{ id: 'line:COST_OF_SALES', column: 'LINE', label: 'Cost of sales', value: money('1800.00') }],
  },
}

function serve(dashboard: unknown) {
  vi.mocked(apiClient).mockImplementation((url: string) => {
    if (url.startsWith('/api/dashboard')) return Promise.resolve(dashboard)
    if (url.startsWith('/api/workspace')) return Promise.resolve({ orgId: 'org_1', name: 'Synthetic Roasters', currency: 'MYR' })
    return Promise.resolve({})
  })
}

describe('DashboardPage', () => {
  let queryClient: QueryClient

  beforeEach(() => {
    queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    vi.clearAllMocks()
  })

  function renderPage() {
    return render(
      <MemoryRouter>
        <QueryClientProvider client={queryClient}>
          <DashboardPage />
        </QueryClientProvider>
      </MemoryRouter>,
    )
  }

  it('says where the books stand, with the period figures from the API (AC-010-1)', async () => {
    serve(DASHBOARD)
    renderPage()

    await waitFor(() => expect(screen.getByText('1 of 3 months are reconciled.')).toBeInTheDocument())
    expect(screen.getByText('2 findings are open.')).toBeInTheDocument()
    expect(screen.getByText('Synthetic Roasters, July to September 2026')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'See August' })).toHaveAttribute('href', '/months/2026-08')

    const figures = screen.getByRole('region', { name: /Figures for July to September 2026/ })
    expect(within(figures).getByText('4,887.94')).toBeInTheDocument()
    expect(within(figures).getByText('Previous period: 4,100.00')).toBeInTheDocument()
    expect(within(figures).getByText('-943.51')).toBeInTheDocument()
    expect(within(figures).getByText('Taken from the balances')).toBeInTheDocument()
    expect(within(figures).getByText('89.6%')).toBeInTheDocument()
    expect(within(figures).getByRole('link', { name: '2 documents to decide on' })).toBeInTheDocument()
    expect(figures.textContent).not.toMatch(/MYR\s*MYR/)
  })

  it('links each alert and month to its page (AC-010-2, AC-010-9)', async () => {
    serve(DASHBOARD)
    renderPage()

    await waitFor(() =>
      expect(screen.getByRole('link', { name: /Invoices from an unknown supplier/ })).toHaveAttribute('href', '/risk/fnd_2'),
    )
    const months = screen.getByRole('region', { name: 'Months' })
    expect(within(months).getAllByRole('link').map((a) => a.getAttribute('href'))).toEqual([
      '/months',
      '/months/2026-07',
      '/months/2026-08',
      '/months/2026-09',
    ])
    expect(within(months).getByText('86%')).toBeInTheDocument()
    expect(within(months).getByText('0 of 1 statements')).toBeInTheDocument()
    expect(screen.getByText('Daybreak Cafe')).toBeInTheDocument()
    expect(screen.getByText('Cost of sales')).toBeInTheDocument()
  })

  it('previews the review queue and links each item and the figure to it (AC-010-1, AC-010-2)', async () => {
    serve(DASHBOARD)
    renderPage()

    const preview = await screen.findByRole('region', { name: 'To review' })
    expect(within(preview).getByRole('link', { name: /Confirm the payment of MYR 1,800.00/ })).toHaveAttribute(
      'href',
      '/review/itm_0000000000000001',
    )
    expect(within(preview).getByText('Choose a match, August 2026')).toBeInTheDocument()
    const figures = screen.getByRole('region', { name: /Figures for/ })
    expect(within(figures).getByRole('link', { name: '3 items to decide' })).toHaveAttribute('href', '/review')
  })

  it('asks for the current month first, then the period chosen (AC-010-1)', async () => {
    vi.useFakeTimers({ toFake: ['Date'] })
    vi.setSystemTime(new Date('2026-09-15T05:00:00Z'))
    serve(DASHBOARD)
    renderPage()

    await waitFor(() => expect(apiClient).toHaveBeenCalledWith('/api/dashboard?period=2026-09'))
    fireEvent.click(await screen.findByRole('button', { name: 'Range' }))
    await waitFor(() => expect(apiClient).toHaveBeenCalledWith('/api/dashboard?period=2026-07..2026-09'))
    vi.useRealTimers()
  })

  it('guides the first upload when there is nothing yet (AC-001-3, AC-010-3)', async () => {
    serve({ ...DASHBOARD, periodMonths: [], kpis: [], months: [], alerts: [] })
    renderPage()

    expect(await screen.findByText('Upload your first documents')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Upload documents/ })).toBeInTheDocument()
  })
})
