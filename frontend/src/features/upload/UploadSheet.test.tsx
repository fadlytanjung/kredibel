import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { StrictMode } from 'react'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { apiClient, ProblemError } from '../../shared/api/client'
import { UploadSheet } from './UploadSheet'

vi.mock('../../shared/api/client', () => ({
  apiClient: vi.fn(),
  ProblemError: class ProblemError extends Error {
    code: string
    status: number
    constructor(problem: { code: string; status: number; detail?: string; title?: string }) {
      super(problem.detail || problem.title)
      this.code = problem.code
      this.status = problem.status
    }
  },
}))

describe('UploadSheet', () => {
  let queryClient: QueryClient

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    })
    vi.clearAllMocks()
  })

  function renderSheet(onUploaded = vi.fn()) {
    return render(
      <MemoryRouter>
        <QueryClientProvider client={queryClient}>
          <UploadSheet onUploaded={onUploaded} />
        </QueryClientProvider>
      </MemoryRouter>,
    )
  }

  it('sends each file once, even in StrictMode (two documents were created for one drop)', async () => {
    vi.mocked(apiClient).mockResolvedValue({
      docId: 'doc_1',
      fileName: 'RHB.pdf',
      status: 'UPLOADED',
      uploadedAt: new Date().toISOString(),
    })
    render(
      <StrictMode>
        <MemoryRouter>
          <QueryClientProvider client={queryClient}>
            <UploadSheet />
          </QueryClientProvider>
        </MemoryRouter>
      </StrictMode>,
    )
    const file = new File(['%PDF-1.7'], 'RHB.pdf', { type: 'application/pdf' })
    fireEvent.drop(screen.getByText('Drop statements, invoices, receipts or a ledger export').closest('section')!, {
      dataTransfer: { files: [file] },
    })

    await waitFor(() => expect(screen.getByText('RHB.pdf')).toBeInTheDocument())
    await waitFor(() => expect(apiClient).toHaveBeenCalled())
    await new Promise((resolve) => setTimeout(resolve, 50))
    expect(vi.mocked(apiClient).mock.calls.filter(([path]) => path === '/api/documents')).toHaveLength(1)
  })

  it('renders drop zone with Choose files and Photo of a receipt buttons', () => {
    renderSheet()
    expect(screen.getByText('Drop statements, invoices, receipts or a ledger export')).toBeInTheDocument()
    expect(screen.getByText('Choose files')).toBeInTheDocument()
    expect(screen.getByText('Photo of a receipt')).toBeInTheDocument()

    const cameraInput = screen.getByTestId('camera-input')
    expect(cameraInput).toHaveAttribute('capture', 'environment')
    expect(cameraInput).toHaveAttribute('accept', 'image/*')
  })

  it('uploads a file successfully and shows done status with link', async () => {
    const mockDoc = {
      docId: 'doc_123',
      fileName: 'statement.pdf',
      contentType: 'application/pdf',
      docType: 'BANK_STATEMENT',
      status: 'UPLOADED',
      uploadedAt: new Date().toISOString(),
    }
    vi.mocked(apiClient).mockResolvedValueOnce(mockDoc)

    const onUploaded = vi.fn()
    renderSheet(onUploaded)

    const file = new File(['%PDF-1.4 test content'], 'statement.pdf', { type: 'application/pdf' })
    const fileInput = screen.getByTestId('file-input')

    fireEvent.change(fileInput, { target: { files: [file] } })

    await waitFor(() => {
      expect(screen.getByText('statement.pdf')).toBeInTheDocument()
    })

    await waitFor(() => {
      expect(apiClient).toHaveBeenCalledWith(
        '/api/documents',
        expect.objectContaining({ method: 'POST' }),
      )
    })

    await waitFor(() => {
      expect(onUploaded).toHaveBeenCalledWith(mockDoc)
    })
  })

  it('displays duplicate notice when file is an exact duplicate (AC-003-6)', async () => {
    const mockDuplicateDoc = {
      docId: 'doc_dup_456',
      fileName: 'BCA Feb.pdf',
      contentType: 'application/pdf',
      docType: 'BANK_STATEMENT',
      status: 'DUPLICATE',
      duplicate: {
        kind: 'EXACT',
        code: 'D01_EXACT_FILE_DUPLICATE',
        ofDocId: 'doc_orig_123',
        decision: 'CONFIRMED',
      },
      uploadedAt: '2026-02-03T10:00:00Z',
    }
    vi.mocked(apiClient).mockResolvedValueOnce(mockDuplicateDoc)

    renderSheet()

    const file = new File(['%PDF-1.4 duplicate'], 'BCA Feb.pdf', { type: 'application/pdf' })
    const fileInput = screen.getByTestId('file-input')

    fireEvent.change(fileInput, { target: { files: [file] } })

    await waitFor(() => {
      expect(screen.getByText('BCA Feb.pdf')).toBeInTheDocument()
    })

    await waitFor(() => {
      expect(screen.getByText(/Already uploaded as/i)).toBeInTheDocument()
      expect(screen.getByRole('link', { name: 'an earlier file' })).toHaveAttribute('href', '/documents/doc_orig_123')
    })

  })

  it('displays error message when upload fails with problem error', async () => {
    vi.mocked(apiClient).mockRejectedValueOnce(
      new ProblemError({
        type: 'about:blank',
        code: 'DOCUMENT_TOO_LARGE',
        status: 413,
        detail: 'The file is 15 MB; the limit is 10 MB.',
        title: 'File too large',
      }),
    )

    renderSheet()

    const file = new File(['huge file content'], 'large.pdf', { type: 'application/pdf' })
    const fileInput = screen.getByTestId('file-input')

    fireEvent.change(fileInput, { target: { files: [file] } })

    await waitFor(() => {
      expect(screen.getByText(/The file is 15 MB/i)).toBeInTheDocument()
    })
  })
})
