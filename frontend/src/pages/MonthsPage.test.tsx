import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
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
      <MemoryRouter>
        <QueryClientProvider client={queryClient}>
          <MonthsPage />
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
    expect(screen.getAllByRole('link', { name: /View/ })[0]).toHaveAttribute('href', '/months/2026-03')
    expect(screen.queryByText('Daybreak Café')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Bank evidence' })).not.toBeInTheDocument()
  })
})
