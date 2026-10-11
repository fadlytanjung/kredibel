import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { apiClient } from '../shared/api/client'
import { DocumentsPage } from './DocumentsPage'

vi.mock('../shared/api/client', () => ({
  apiClient: vi.fn(),
  ProblemError: class ProblemError extends Error {},
}))

describe('DocumentsPage', () => {
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
          <DocumentsPage />
        </QueryClientProvider>
      </MemoryRouter>,
    )
  }

  it('renders page header and empty state when no documents exist', async () => {
    vi.mocked(apiClient).mockResolvedValueOnce({ items: [], nextCursor: null })

    renderPage()

    expect(screen.getByText('Documents')).toBeInTheDocument()
    expect(
      screen.getByText(
        'Everything you uploaded, in any order. Kredibel reads each file twice and checks it before its numbers count.',
      ),
    ).toBeInTheDocument()

    await waitFor(() => {
      expect(
        screen.getByText('No documents yet. Drop your first statement, invoice or receipt above.'),
      ).toBeInTheDocument()
    })
  })

  it('renders document rows with badges and handles filter chips (AC-003-7)', async () => {
    const mockDocs = [
      {
        docId: 'doc_1',
        fileName: 'BCA_Mar_2026.pdf',
        contentType: 'application/pdf',
        docType: 'BANK_STATEMENT',
        status: 'DONE',
        pageCount: 3,
        months: ['2026-03'],
        integrity: { verdict: 'CLEAN' },
        risk: { level: 'LOW' },
        uploadedAt: '2026-03-02T10:00:00Z',
      },
      {
        docId: 'doc_2',
        fileName: 'Invoice_Daybreak.pdf',
        contentType: 'application/pdf',
        docType: 'SALES_INVOICE',
        status: 'READING',
        pageCount: 1,
        months: ['2026-03'],
        uploadedAt: '2026-03-05T12:00:00Z',
      },
    ]

    vi.mocked(apiClient).mockResolvedValueOnce({ items: mockDocs, nextCursor: null })

    renderPage()

    await waitFor(() => {
      expect(screen.getByText('BCA_Mar_2026.pdf')).toBeInTheDocument()
      expect(screen.getByText('Invoice_Daybreak.pdf')).toBeInTheDocument()
    })

    // Check integrity badge and risk level
    expect(screen.getByText('Clean')).toBeInTheDocument()
    expect(screen.getAllByText('LOW').length).toBeGreaterThan(0)

    // Test filter chip click
    vi.mocked(apiClient).mockResolvedValueOnce({
      items: [mockDocs[0]],
      nextCursor: null,
    })

    const statementsChip = screen.getByRole('button', { name: 'Statements' })
    fireEvent.click(statementsChip)

    await waitFor(() => {
      expect(apiClient).toHaveBeenCalledWith(
        expect.stringContaining('type=BANK_STATEMENT'),
      )
    })
  })
})
