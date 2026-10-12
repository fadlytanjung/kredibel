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

  it('lists the lines read and points at a value on its page (T005-11)', async () => {
    const box = { x0: 0.62, y0: 0.3, x1: 0.7, y1: 0.31 }
    const reading = (status: string) => ({ status, page: 2, bbox: box, sources: ['GEMINI', 'TEXT_LAYER'] })
    const doc = {
      docId: 'doc_lines',
      fileName: 'RHB.pdf',
      contentType: 'application/pdf',
      docType: 'BANK_STATEMENT',
      status: 'DONE',
      pageCount: 2,
      pages: [
        { pageNo: 1, status: 'DONE', textLayer: true, witness: 'TEXT_LAYER' },
        { pageNo: 2, status: 'DONE', textLayer: true, witness: 'TEXT_LAYER' },
      ],
      reading: { method: 'AI_TEXT_LAYER', agreement: '1.000', fieldsCompared: 8, fieldsAgreed: 8, lines: 2 },
      statementMeta: {
        bankName: 'RHB Bank Berhad',
        accountMasked: '••••3876',
        periodStart: '2026-08-16',
        periodEnd: '2026-09-15',
        opening: { amount: '1216.73', currency: 'MYR' },
        closing: { amount: '1454.33', currency: 'MYR' },
      },
      uploadedAt: '2026-10-12T01:57:18Z',
    }
    const line = (txId: string, page: number, amount: string, description: string, status = 'AGREED') => ({
      txId,
      docId: 'doc_lines',
      page,
      rowIndex: 0,
      date: '2026-09-02',
      month: '2026-09',
      description,
      counterpartyName: null,
      amount: { amount, currency: 'MYR' },
      balance: { amount: '1454.33', currency: 'MYR' },
      readings: { amount: { ...reading(status), page }, date: reading('AGREED') },
      match: { state: 'UNMATCHED' },
    })
    vi.mocked(apiClient).mockImplementation(async (path: string) =>
      path.startsWith('/api/bank-lines')
        ? {
            items: [
              line('tx_1', 1, '-12.40', 'DEBIT CARD TXN-DR\nGRAB RIDES'),
              line('tx_2', 2, '250.00', 'MBK INSTANT TRF CR\nNURUL AINA', 'CONFLICT'),
            ],
          }
        : doc,
    )

    renderPage('doc_lines')

    await waitFor(() => expect(screen.getByText('Transactions read')).toBeInTheDocument())
    expect(apiClient).toHaveBeenCalledWith('/api/bank-lines?docId=doc_lines')
    expect(screen.getByText('2 lines; 8 of 8 values found on the page')).toBeInTheDocument()
    expect(screen.getByText('On the page')).toBeInTheDocument()
    expect(screen.getByText('Readings differ')).toBeInTheDocument()
    expect(screen.getByText(/1,216\.73/)).toBeInTheDocument()
    expect(screen.queryByTestId('page-lamp')).not.toBeInTheDocument()

    fireEvent.click(screen.getByText('MBK INSTANT TRF CR'))

    await waitFor(() => expect(screen.getByTestId('page-lamp')).toBeInTheDocument())
    expect(apiBlob).toHaveBeenCalledWith('/api/documents/doc_lines/pages/2?variant=full')
    expect(screen.getByTestId('page-lamp').style.left).toBe('61.6%')
  })

  it('shows the invoices read from a document and lights a value on its page (T005-03)', async () => {
    const box = { x0: 0.7, y0: 0.5, x1: 0.85, y1: 0.52 }
    const agreed = { status: 'AGREED', page: 1, bbox: box, sources: ['GEMINI', 'TEXT_LAYER'] }
    vi.mocked(apiClient).mockImplementation(async (path: string) =>
      path.startsWith('/api/invoices')
        ? {
            items: [
              {
                invoiceId: 'inv_0000000000000001',
                docId: 'doc_inv',
                kind: 'SALES',
                number: 'INV/SCR/2026/03/0009',
                issuerName: 'Sunrise Coffee Roasters',
                buyerName: 'Daybreak Café',
                issueDate: '2026-03-12',
                total: { amount: '19597050.00', currency: 'IDR' },
                tax: { amount: '1942050.00', currency: 'IDR' },
                lines: [{ description: 'Drip bags, box of 20', qty: '93', amount: { amount: '8835000.00', currency: 'IDR' } }],
                payment: { state: 'UNPAID' },
                readings: { total: agreed, number: { ...agreed, bbox: undefined }, 'lines.0.amount': agreed },
              },
            ],
          }
        : {
            docId: 'doc_inv',
            fileName: 'invoice.pdf',
            contentType: 'application/pdf',
            docType: 'SALES_INVOICE',
            status: 'DONE',
            pageCount: 1,
            pages: [{ pageNo: 1, status: 'DONE', textLayer: true, witness: 'TEXT_LAYER' }],
            reading: { method: 'AI_TEXT_LAYER', agreement: '1.000', fieldsCompared: 12, fieldsAgreed: 12, lines: 1 },
            uploadedAt: '2026-10-12T01:57:18Z',
          },
    )

    renderPage('doc_inv')

    await waitFor(() => expect(screen.getByText('INV/SCR/2026/03/0009')).toBeInTheDocument())
    expect(apiClient).toHaveBeenCalledWith('/api/invoices?docId=doc_inv')
    expect(screen.getByText('Sales invoice')).toBeInTheDocument()
    expect(screen.getByText('12 of 12 values found on the page')).toBeInTheDocument()
    expect(screen.getByText('Daybreak Café')).toBeInTheDocument()
    expect(screen.queryByTestId('page-lamp')).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /Total/ }))

    await waitFor(() => expect(screen.getByTestId('page-lamp')).toBeInTheDocument())
    expect(screen.getByTestId('page-lamp').style.left).toBe('69.6%')
  })
})
