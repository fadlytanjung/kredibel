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
    expect(screen.queryByRole('button', { name: 'Bank evidence' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Needs review/ })).toHaveTextContent('1')
    fireEvent.change(screen.getByRole('textbox', { name: /Search/i }), { target: { value: 'january' } })
    expect(screen.queryByText('March 2026')).not.toBeInTheDocument()
    fireEvent.click(screen.getByText('January 2026'))
    expect(screen.getByText('Month page')).toBeInTheDocument()
  })
})
