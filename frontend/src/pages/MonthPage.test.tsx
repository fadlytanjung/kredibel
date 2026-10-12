import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { apiClient } from '../shared/api/client'
import { MonthPage } from './MonthPage'

vi.mock('../shared/api/client', () => ({
  apiClient: vi.fn(),
  ProblemError: class ProblemError extends Error {},
}))

vi.mock('../entities/month/useMonthLive', () => ({
  useMonthLive: () => ({
    month: { month: '2026-03', state: 'RECONCILED' },
    loading: false,
    error: null,
  }),
}))

describe('MonthPage', () => {
  let queryClient: QueryClient

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })
    vi.clearAllMocks()
  })

  function renderPage(month = '2026-03') {
    return render(
      <MemoryRouter initialEntries={[`/months/${month}`]}>
        <QueryClientProvider client={queryClient}>
          <Routes>
            <Route path="/months/:month" element={<MonthPage />} />
          </Routes>
        </QueryClientProvider>
      </MemoryRouter>,
    )
  }

  it('renders month figures, bank lines, and match chips (AC-007-12)', async () => {
    vi.mocked(apiClient).mockImplementation((url: string) => {
      if (url.includes('/api/months/2026-03')) {
        return Promise.resolve({
          month: '2026-03',
          state: 'RECONCILED',
          figures: {
            opening_balance: '47900000.00',
            money_in: '231400000.00',
            money_out: '218900000.00',
            closing_balance: '60400000.00',
            match_rate: '86%',
            ledger_difference: '0.00',
          },
        })
      }
      if (url.includes('/api/bank-lines?month=2026-03')) {
        return Promise.resolve({
          items: [
            {
              txId: 'tx_1',
              date: '2026-03-11',
              description: 'TRANSFER IN DAYBREAK CAFE',
              amount: { amount: '6420000.00', currency: 'IDR' },
              category: 'Sales',
              match: { state: 'CONFIRMED', matchIds: ['mat_1'] },
            },
            {
              txId: 'tx_2',
              date: '2026-03-12',
              description: 'TRANSFER OUT GREEN VALLEY FARMS',
              amount: { amount: '-9850000.00', currency: 'IDR' },
              category: 'Supplier',
              match: { state: 'UNMATCHED', matchIds: [] },
              support: 'Bank recorded · No supporting document',
            },
          ],
          nextCursor: null,
        })
      }
      if (url.includes('/api/matches?month=2026-03')) {
        return Promise.resolve({
          items: [
            {
              matchId: 'mat_1',
              month: '2026-03',
              method: 'AUTO',
              status: 'CONFIRMED',
              reasons: ['Same amount', 'Same client'],
            },
          ],
        })
      }
      if (url.includes('/api/workspace')) {
        return Promise.resolve({ orgId: 'org_1', currency: 'IDR' })
      }
      return Promise.resolve({})
    })

    renderPage()

    expect(screen.getByText('March 2026')).toBeInTheDocument()
    expect(screen.getByText('Opening balance')).toBeInTheDocument()
    expect(screen.getAllByText('Money in')[0]).toBeInTheDocument()
    expect(screen.getByText('Closing balance')).toBeInTheDocument()

    await waitFor(() => {
      expect(screen.getByText('TRANSFER IN DAYBREAK CAFE')).toBeInTheDocument()
      expect(screen.getByText('TRANSFER OUT GREEN VALLEY FARMS')).toBeInTheDocument()
      expect(screen.getByText('Matched to document')).toBeInTheDocument()
      expect(screen.getByText('No supporting document')).toBeInTheDocument()
    })
  })

  it('unmatch button calls unmatch API (AC-007-13)', async () => {
    vi.mocked(apiClient).mockImplementation((url: string, opts?: RequestInit) => {
      if (opts?.method === 'DELETE') {
        return Promise.resolve({})
      }
      if (url.includes('/api/months/2026-03')) {
        return Promise.resolve({ month: '2026-03', state: 'RECONCILED' })
      }
      if (url.includes('/api/bank-lines?month=2026-03')) {
        return Promise.resolve({
          items: [
            {
              txId: 'tx_1',
              date: '2026-03-11',
              description: 'TRANSFER IN DAYBREAK CAFE',
              amount: { amount: '6420000.00', currency: 'IDR' },
              category: 'Sales',
              match: { state: 'CONFIRMED', matchIds: ['mat_1'] },
            },
          ],
          nextCursor: null,
        })
      }
      if (url.includes('/api/matches?month=2026-03')) {
        return Promise.resolve({
          items: [
            {
              matchId: 'mat_1',
              month: '2026-03',
              method: 'MANUAL',
              status: 'CONFIRMED',
              reasons: ['Matched by you'],
            },
          ],
        })
      }
      if (url.includes('/api/workspace')) {
        return Promise.resolve({ orgId: 'org_1', currency: 'IDR' })
      }
      return Promise.resolve({})
    })

    renderPage()

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Unmatch' })).toBeInTheDocument()
    })

    fireEvent.click(screen.getByRole('button', { name: 'Unmatch' }))

    await waitFor(() => {
      expect(apiClient).toHaveBeenCalledWith(
        '/api/matches/mat_1',
        expect.objectContaining({ method: 'DELETE' }),
      )
    })
  })

  it('supports searching bank lines in DataTable', async () => {
    vi.mocked(apiClient).mockImplementation((url: string) => {
      if (url.includes('/api/months/2026-03')) {
        return Promise.resolve({ month: '2026-03', state: 'RECONCILED' })
      }
      if (url.includes('/api/bank-lines?month=2026-03')) {
        return Promise.resolve({
          items: [
            {
              txId: 'tx_1',
              date: '2026-03-11',
              description: 'TRANSFER IN DAYBREAK CAFE',
              amount: { amount: '6420000.00', currency: 'IDR' },
              category: 'Sales',
              match: { state: 'CONFIRMED', matchIds: ['mat_1'] },
            },
            {
              txId: 'tx_2',
              date: '2026-03-12',
              description: 'TRANSFER OUT GREEN VALLEY FARMS',
              amount: { amount: '-9850000.00', currency: 'IDR' },
              category: 'Supplier',
              match: { state: 'UNMATCHED', matchIds: [] },
              support: 'Bank recorded · No supporting document',
            },
          ],
          nextCursor: null,
        })
      }
      if (url.includes('/api/matches?month=2026-03')) {
        return Promise.resolve({ items: [] })
      }
      if (url.includes('/api/workspace')) {
        return Promise.resolve({ orgId: 'org_1', currency: 'IDR' })
      }
      return Promise.resolve({})
    })

    renderPage()

    await waitFor(() => {
      expect(screen.getByText('TRANSFER IN DAYBREAK CAFE')).toBeInTheDocument()
      expect(screen.getByText('TRANSFER OUT GREEN VALLEY FARMS')).toBeInTheDocument()
    })

    // Search for DAYBREAK
    const searchInput = screen.getByRole('textbox', { name: /Search/i })
    fireEvent.change(searchInput, { target: { value: 'DAYBREAK' } })

    expect(screen.getByText('TRANSFER IN DAYBREAK CAFE')).toBeInTheDocument()
    expect(screen.queryByText('TRANSFER OUT GREEN VALLEY FARMS')).not.toBeInTheDocument()
  })
})
