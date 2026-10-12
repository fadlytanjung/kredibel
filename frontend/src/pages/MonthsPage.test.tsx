import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
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

  it('switches between ADR-025 tabs: bank evidence, documents first and currency check', async () => {
    vi.mocked(apiClient).mockImplementation((url: string) => {
      if (url.includes('/api/months')) {
        return Promise.resolve({
          items: [{ month: '2026-03', state: 'RECONCILED', statements: ['doc_1'] }],
        })
      }
      if (url.includes('/api/workspace')) {
        return Promise.resolve({ orgId: 'org_1', currency: 'MYR' })
      }
      return Promise.resolve({})
    })

    renderPage()

    await waitFor(() => {
      expect(screen.getByText('2026-03')).toBeInTheDocument()
    })

    // Click Bank evidence tab
    fireEvent.click(screen.getByRole('button', { name: 'Bank evidence' }))
    expect(screen.getByText('4 bank transactions, 3 supporting invoices')).toBeInTheDocument()
    expect(screen.getByText('Daybreak Café')).toBeInTheDocument()

    // Click Documents first tab
    fireEvent.click(screen.getByRole('button', { name: 'Documents first' }))
    expect(screen.getByText('Your documents are ready for the statement')).toBeInTheDocument()
    expect(screen.getByText('Primepack Packaging')).toBeInTheDocument()

    // Click Currency check tab
    fireEvent.click(screen.getByRole('button', { name: 'Currency check' }))
    expect(screen.getByText('Confirm document currency')).toBeInTheDocument()
    expect(screen.getByText('Use amounts as MYR')).toBeInTheDocument()
  })
})
