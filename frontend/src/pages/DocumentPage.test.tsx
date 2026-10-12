import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { apiBlob, apiClient } from '../shared/api/client'
import { DocumentPage } from './DocumentPage'

vi.mock('../shared/api/client', () => ({
  apiClient: vi.fn(),
  apiBlob: vi.fn(async () => new Blob(['png'], { type: 'image/png' })),
  ProblemError: class ProblemError extends Error {},
}))

// jsdom has no object URLs.
URL.createObjectURL = vi.fn((blob: Blob) => `blob:test/${blob.size}`)
URL.revokeObjectURL = vi.fn()

describe('DocumentPage', () => {
  let queryClient: QueryClient

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    })
    vi.clearAllMocks()
  })

  function renderPage(docId = 'doc_test_123') {
    return render(
      <MemoryRouter initialEntries={[`/documents/${docId}`]}>
        <QueryClientProvider client={queryClient}>
          <Routes>
            <Route path="/documents/:docId" element={<DocumentPage />} />
            <Route path="/documents" element={<div>Documents List View</div>} />
          </Routes>
        </QueryClientProvider>
      </MemoryRouter>,
    )
  }

  it('renders document details, pages, and extracted values (AC-003-9)', async () => {
    const mockDoc = {
      docId: 'doc_test_123',
      fileName: 'BCA_Statement_March.pdf',
      contentType: 'application/pdf',
      docType: 'BANK_STATEMENT',
      status: 'DONE',
      pageCount: 2,
      pages: [
        { pageNo: 1, status: 'DONE', textLayer: true, witness: 'TEXT_LAYER' },
        { pageNo: 2, status: 'DONE', textLayer: true, witness: 'TEXT_LAYER' },
      ],
      statementMeta: {
        bankName: 'Bank Central Asia',
        accountMasked: '••••4821',
        periodStart: '2026-03-01',
        periodEnd: '2026-03-31',
      },
      integrity: { verdict: 'CLEAN' },
      uploadedAt: '2026-03-02T10:00:00Z',
    }

    vi.mocked(apiClient).mockResolvedValueOnce(mockDoc)

    renderPage()

    await waitFor(() => {
      expect(screen.getByText('BCA_Statement_March.pdf')).toBeInTheDocument()
      expect(screen.getByText('Bank Central Asia')).toBeInTheDocument()
      expect(screen.getByText('••••4821')).toBeInTheDocument()
    })

    // Check pages viewer
    expect(screen.getByText('Pages (2)')).toBeInTheDocument()
  })

  it('loads page images and the original with the token (they came back 401 as <img src>)', async () => {
    vi.mocked(apiClient).mockResolvedValueOnce({
      docId: 'doc_img',
      fileName: 'RHB.pdf',
      contentType: 'application/pdf',
      docType: 'BANK_STATEMENT',
      status: 'UPLOADED',
      pageCount: 2,
      pages: [
        { pageNo: 1, status: 'PENDING', textLayer: true, witness: 'TEXT_LAYER' },
        { pageNo: 2, status: 'PENDING', textLayer: true, witness: 'TEXT_LAYER' },
      ],
      uploadedAt: '2026-10-12T01:57:18Z',
    })
    renderPage('doc_img')

    await waitFor(() => expect(apiBlob).toHaveBeenCalledWith('/api/documents/doc_img/pages/1?variant=thumb'))
    expect(apiBlob).toHaveBeenCalledWith('/api/documents/doc_img/pages/1?variant=full')
    await waitFor(() =>
      expect(
        screen.getAllByRole('img', { name: 'Page 1' }).some((el) => el.getAttribute('src')?.startsWith('blob:')),
      ).toBe(true),
    )
    expect(screen.queryByRole('link', { name: /Original file/i })).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /Original file/i }))
    await waitFor(() => expect(apiBlob).toHaveBeenCalledWith('/api/documents/doc_img/file'))
  })

  it('handles document deletion with confirmation dialog (AC-003-10)', async () => {
    const mockDoc = {
      docId: 'doc_del_999',
      fileName: 'To_Delete.pdf',
      contentType: 'application/pdf',
      docType: 'RECEIPT',
      status: 'DONE',
      pageCount: 1,
      uploadedAt: '2026-03-02T10:00:00Z',
    }

    vi.mocked(apiClient).mockResolvedValueOnce(mockDoc)
    vi.mocked(apiClient).mockResolvedValueOnce({}) // DELETE call

    renderPage('doc_del_999')

    await waitFor(() => {
      expect(screen.getByText('To_Delete.pdf')).toBeInTheDocument()
    })

    // Click remove document button
    const deleteBtn = screen.getByRole('button', { name: /Remove document/i })
    fireEvent.click(deleteBtn)

    // Confirmation banner appears
    await waitFor(() => {
      expect(screen.getByText(/Are you sure you want to remove To_Delete.pdf/i)).toBeInTheDocument()
    })

    // Confirm removal
    const confirmBtn = screen.getByRole('button', { name: /^Remove$/i })
    fireEvent.click(confirmBtn)

    await waitFor(() => {
      expect(apiClient).toHaveBeenCalledWith('/api/documents/doc_del_999', {
        method: 'DELETE',
      })
    })

    // Navigates back to /documents
    await waitFor(() => {
      expect(screen.getByText('Documents List View')).toBeInTheDocument()
    })
  })
})
