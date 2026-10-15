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

    // Filters work in the table with counts; search by name; 10 rows a page.
    fireEvent.click(screen.getByRole('button', { name: /Statements/ }))
    expect(screen.getByText('BCA_Mar_2026.pdf')).toBeInTheDocument()
    expect(screen.queryByText('Invoice_Daybreak.pdf')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: /Statements/ })).toHaveTextContent('1')
    fireEvent.click(screen.getByRole('button', { name: /^All/ }))
    fireEvent.change(screen.getByRole('textbox', { name: /Search/i }), { target: { value: 'daybreak' } })
    expect(screen.getByText('Invoice_Daybreak.pdf')).toBeInTheDocument()
    expect(screen.queryByText('BCA_Mar_2026.pdf')).not.toBeInTheDocument()
    expect(apiClient).not.toHaveBeenCalledWith(expect.stringContaining('type=BANK_STATEMENT'))
  })

  it('pages the library ten documents at a time', async () => {
    const docs = Array.from({ length: 23 }, (_, i) => ({
      docId: `doc_${i}`,
      fileName: `receipt-${String(i).padStart(2, '0')}.pdf`,
      contentType: 'application/pdf',
      docType: 'RECEIPT',
      status: 'DONE',
      pageCount: 1,
      months: ['2026-03'],
      uploadedAt: `2026-03-${String(i + 1).padStart(2, '0')}T10:00:00Z`,
    }))
    vi.mocked(apiClient).mockResolvedValueOnce({ items: docs, nextCursor: null })

    renderPage()

    await waitFor(() => expect(screen.getByText('1 to 10 of 23')).toBeInTheDocument())
    expect(screen.getByRole('button', { name: /Receipts/ })).toHaveTextContent('23')
  })

  it('says an exact copy is not checked instead of "Checking" forever', async () => {
    vi.mocked(apiClient).mockResolvedValueOnce({
      items: [
        { docId: 'doc_copy', fileName: 'ACB_Feb_2026 (1).pdf', contentType: 'application/pdf', docType: 'BANK_STATEMENT', status: 'DUPLICATE', pageCount: 3, months: ['2026-02'], uploadedAt: '2026-07-02T10:00:00Z' },
        { docId: 'doc_ledger', fileName: 'ledger.csv', contentType: 'text/csv', docType: 'UNKNOWN', status: 'NEEDS_INPUT', pageCount: 0, months: [], uploadedAt: '2026-07-02T10:01:00Z' },
      ],
      nextCursor: null,
    })

    renderPage()

    await waitFor(() => expect(screen.getByText('ACB_Feb_2026 (1).pdf')).toBeInTheDocument())
    expect(screen.getByText('Copy, not checked')).toBeInTheDocument()
    expect(screen.getByText('Not checked')).toBeInTheDocument()
    expect(screen.queryByText('Checking')).not.toBeInTheDocument()
  })
})
