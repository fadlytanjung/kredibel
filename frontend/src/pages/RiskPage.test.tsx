/**
 * Tests for RiskPage and EvidenceViewer (spec 008, AC-008-7, AC-008-8, AC-008-9, AC-008-10).
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { apiClient } from '../shared/api/client'
import { RiskPage } from './RiskPage'

vi.mock('../shared/api/client', () => ({
  apiClient: vi.fn(),
  ProblemError: class ProblemError extends Error {},
}))

const MOCK_DASHBOARD = {
  period: 'all',
  kpis: [],
  months: [
    { month: '2026-01', state: 'RECONCILED', riskLevel: 'LOW', autoMatchRate: '0.9400', statementsPresent: 1, statementsExpected: 1 },
    { month: '2026-03', state: 'NEEDS_REVIEW', riskLevel: 'CRITICAL', autoMatchRate: '0.8600', statementsPresent: 1, statementsExpected: 1 },
    { month: '2026-05', state: 'NEEDS_REVIEW', riskLevel: 'HIGH', autoMatchRate: '0.8800', statementsPresent: 1, statementsExpected: 1 },
  ],
}

const MOCK_FINDING_A01 = {
  findingId: 'fnd_0123456789abcdef',
  code: 'A01_RUNNING_BALANCE_BREAK',
  category: 'ARITHMETIC',
  scope: 'MONTH',
  month: '2026-03',
  docId: 'ACB_Mar_2026.pdf',
  severity: 'CRITICAL',
  title: 'Running balance does not add up on 14 Mar',
  facts: {
    previousBalance: '41,250,000.00',
    credit: '7,250,000.00',
    expectedBalance: '48,500,000.00',
    printedBalance: '42,500,000.00',
    difference: '6,000,000.00',
  },
  explanation:
    'The balance printed on 14 Mar is IDR 6,000,000 lower than the previous balance plus credit.',
  nextSteps: [
    'Download the March statement again from internet banking and upload it.',
    'Ask who sent you this file.',
  ],
  evidence: [
    {
      field: 'Credit, 14 Mar',
      value: '7,250,000.00',
      grounded: 'AGREED',
      page: 2,
      bbox: { x0: 0.5, y0: 0.5, x1: 0.7, y1: 0.6 },
    },
    {
      field: 'Balance, 14 Mar',
      value: '42,500,000.00',
      grounded: 'AGREED',
      page: 2,
      bbox: { x0: 0.7, y0: 0.5, x1: 0.9, y1: 0.6 },
    },
  ],
  detectedBy: 'MODEL',
  status: 'OPEN',
}

const MOCK_FINDING_X08 = {
  findingId: 'fnd_9876543210fedcba',
  code: 'X08_ACCOUNT_CHANGE',
  category: 'PAYMENT',
  scope: 'MONTH',
  month: '2026-05',
  docId: 'INV_May_2026.pdf',
  severity: 'HIGH',
  title: 'Roastline Equipment Service paid to a new account',
  facts: {
    amount: '24,500,000.00',
  },
  explanation: 'Roastline Equipment Service was paid to a new bank account.',
  nextSteps: ['Confirm the new account with the supplier using a known phone number.'],
  evidence: [],
  detectedBy: 'RULE',
  status: 'OPEN',
}

describe('RiskPage (AC-008-7, AC-008-8, AC-008-9, AC-008-10)', () => {
  let queryClient: QueryClient

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })
    vi.clearAllMocks()
  })

  function renderRiskPage(initialPath = '/risk') {
    return render(
      <MemoryRouter initialEntries={[initialPath]}>
        <QueryClientProvider client={queryClient}>
          <Routes>
            <Route path="/risk" element={<RiskPage />} />
            <Route path="/risk/:findingId" element={<RiskPage />} />
          </Routes>
        </QueryClientProvider>
      </MemoryRouter>,
    )
  }

  it('renders month risk levels and groups findings by month (AC-008-7, AC-008-10)', async () => {
    vi.mocked(apiClient).mockImplementation((path: string) => {
      if (path === '/api/dashboard?period=all') return Promise.resolve(MOCK_DASHBOARD)
      if (path === '/api/documents?limit=200') return Promise.resolve({ items: [] })
      if (path === '/api/findings') {
        return Promise.resolve({
          items: [MOCK_FINDING_A01, MOCK_FINDING_X08],
          nextCursor: null,
        })
      }
      return Promise.reject(new Error(`Unhandled path: ${path}`))
    })

    renderRiskPage()

    // 1. Header attention count
    await waitFor(() => {
      expect(screen.getByText('Risk')).toBeInTheDocument()
      expect(screen.getByText(/2 months need attention: March is critical and May is high/)).toBeInTheDocument()
    })

    // 2. Month tabs at the top have risk badges
    expect(screen.getByText('Mar')).toBeInTheDocument()
    expect(screen.getByText('May')).toBeInTheDocument()

    // 3. Groups findings by month with month headers, the worst month first
    expect(screen.getByText('March 2026')).toBeInTheDocument()
    expect(screen.getByText('May 2026')).toBeInTheDocument()

    // 4. Finding rows with code tag and titles
    expect(
      screen.getByText('Running balance does not add up on 14 Mar'),
    ).toBeInTheDocument()
    expect(
      screen.getByText('Roastline Equipment Service paid to a new account'),
    ).toBeInTheDocument()
  })

  it('names a document that is not among the first page of documents (spec 024)', async () => {
    // A busy workspace has more documents than one page: the held copy is fetched by its ID.
    const held = { ...MOCK_FINDING_A01, findingId: 'fnd_held', docId: 'doc_scan_0001', evidence: [] }
    vi.mocked(apiClient).mockImplementation((path: string) => {
      if (path === '/api/dashboard?period=all') return Promise.resolve(MOCK_DASHBOARD)
      if (path === '/api/documents?limit=200') return Promise.resolve({ items: [] })
      if (path === '/api/documents/doc_scan_0001')
        return Promise.resolve({ docId: 'doc_scan_0001', fileName: 'inv-purchase-2026-08-01-scan.pdf' })
      if (path === '/api/findings') return Promise.resolve({ items: [held], nextCursor: null })
      return Promise.reject(new Error(`Unhandled path: ${path}`))
    })

    renderRiskPage()

    expect((await screen.findAllByText(/inv-purchase-2026-08-01-scan\.pdf/)).length).toBeGreaterThan(0)
    expect(screen.queryByText(/doc_scan_0001/)).toBeNull()
  })

  it('filters findings by severity chips (AC-008-7)', async () => {
    vi.mocked(apiClient).mockImplementation((path: string) => {
      if (path === '/api/dashboard?period=all') return Promise.resolve(MOCK_DASHBOARD)
      if (path === '/api/documents?limit=200') return Promise.resolve({ items: [] })
      if (path === '/api/findings') {
        return Promise.resolve({
          items: [MOCK_FINDING_A01, MOCK_FINDING_X08],
          nextCursor: null,
        })
      }
      return Promise.reject(new Error(`Unhandled path: ${path}`))
    })

    renderRiskPage()

    await waitFor(() => {
      expect(
        screen.getByText('Running balance does not add up on 14 Mar'),
      ).toBeInTheDocument()
    })

    // Click Critical filter chip within chips group
    const chipsGroup = screen.getByRole('group', { name: 'Filter by severity' })
    const criticalChip = within(chipsGroup).getByRole('button', { name: /Critical/ })
    fireEvent.click(criticalChip)

    // A01 remains, X08 (High) is filtered out
    expect(
      screen.getByText('Running balance does not add up on 14 Mar'),
    ).toBeInTheDocument()
    expect(
      screen.queryByText('Roastline Equipment Service paid to a new account'),
    ).not.toBeInTheDocument()
  })

  it('opens evidence viewer on findingId route with calc, readings and next steps (AC-008-8)', async () => {
    vi.mocked(apiClient).mockImplementation((path: string) => {
      if (path === '/api/dashboard?period=all') return Promise.resolve(MOCK_DASHBOARD)
      if (path === '/api/documents?limit=200') return Promise.resolve({ items: [] })
      if (path === '/api/findings') {
        return Promise.resolve({
          items: [MOCK_FINDING_A01, MOCK_FINDING_X08],
          nextCursor: null,
        })
      }
      if (path === `/api/findings/${MOCK_FINDING_A01.findingId}`) {
        return Promise.resolve(MOCK_FINDING_A01)
      }
      return Promise.reject(new Error(`Unhandled path: ${path}`))
    })

    renderRiskPage(`/risk/${MOCK_FINDING_A01.findingId}`)

    // Evidence viewer drawer is visible
    await waitFor(() => {
      expect(
        screen.getAllByText('Running balance does not add up on 14 Mar').length,
      ).toBeGreaterThanOrEqual(1)
      expect(screen.getByText('How the balance should add up')).toBeInTheDocument()
      expect(screen.getByText('Two readings')).toBeInTheDocument()
      expect(screen.getByText('What to do next')).toBeInTheDocument()
    })

    // Breakdown values rendered
    expect(screen.getByText('48,500,000.00')).toBeInTheDocument()
    expect(screen.getByText('6,000,000.00')).toBeInTheDocument()

    // Next steps
    expect(
      screen.getByText(
        'Download the March statement again from internet banking and upload it.',
      ),
    ).toBeInTheDocument()
  })

  it('acknowledges and dismisses findings with reason requirement (AC-008-9)', async () => {
    let currentStatus = 'OPEN'
    let dismissedReason: string | undefined

    vi.mocked(apiClient).mockImplementation((path: string, options?: RequestInit) => {
      if (path === '/api/dashboard?period=all') return Promise.resolve(MOCK_DASHBOARD)
      if (path === '/api/documents?limit=200') return Promise.resolve({ items: [] })
      if (path === '/api/findings') {
        return Promise.resolve({
          items: [{ ...MOCK_FINDING_A01, status: currentStatus, dismissal: dismissedReason ? { reason: dismissedReason } : undefined }],
          nextCursor: null,
        })
      }
      if (path === `/api/findings/${MOCK_FINDING_A01.findingId}`) {
        if (options?.method === 'PATCH') {
          const body = JSON.parse(options.body as string)
          currentStatus = body.status
          dismissedReason = body.reason
          return Promise.resolve({
            ...MOCK_FINDING_A01,
            status: currentStatus,
            dismissal: dismissedReason ? { reason: dismissedReason } : undefined,
          })
        }
        return Promise.resolve({
          ...MOCK_FINDING_A01,
          status: currentStatus,
          dismissal: dismissedReason ? { reason: dismissedReason } : undefined,
        })
      }
      return Promise.reject(new Error(`Unhandled path: ${path}`))
    })

    renderRiskPage(`/risk/${MOCK_FINDING_A01.findingId}`)

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Dismiss/ })).toBeInTheDocument()
    })

    // Click Dismiss to open prompt
    fireEvent.click(screen.getByRole('button', { name: /Dismiss/ }))

    expect(screen.getByText('Dismiss finding')).toBeInTheDocument()

    // Submit with short reason (< 10 chars) -> validation message
    const textarea = screen.getByPlaceholderText(/Verified with bank/)
    fireEvent.change(textarea, { target: { value: 'Too short' } })
    fireEvent.click(screen.getByRole('button', { name: 'Confirm dismissal' }))

    expect(
      screen.getByText(/Reason must be at least 10 characters/),
    ).toBeInTheDocument()

    // Submit with valid reason (>= 10 chars)
    fireEvent.change(textarea, {
      target: { value: 'Verified with bank as legitimate adjustment.' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Confirm dismissal' }))

    await waitFor(() => {
      expect(apiClient).toHaveBeenCalledWith(
        `/api/findings/${MOCK_FINDING_A01.findingId}`,
        expect.objectContaining({
          method: 'PATCH',
          body: JSON.stringify({
            status: 'DISMISSED',
            reason: 'Verified with bank as legitimate adjustment.',
          }),
        }),
      )
    })
  })
})
