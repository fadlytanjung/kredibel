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

  it('renders the document beside its page viewer, with its details (AC-003-9)', async () => {
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

    vi.mocked(apiClient).mockImplementation(async (path: string) =>
      path.startsWith('/api/findings') ? { items: [] } : mockDoc,
    )

    renderPage()

    await waitFor(() => expect(screen.getByRole('heading', { name: 'BCA_Statement_March.pdf' })).toBeInTheDocument())
    expect(screen.getByText(/Bank statement, Bank Central Asia ••••4821/)).toBeInTheDocument()
    expect(screen.getByText('No signs of editing')).toBeInTheDocument()
    expect(screen.getByText('Page 1 of 2')).toBeInTheDocument()
    expect(screen.getByText('Digital')).toBeInTheDocument()

    // Not read yet: the findings and details tabs only; details lists what the file is.
    expect(screen.queryByRole('tab', { name: /Transactions/ })).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('tab', { name: 'Details' }))
    expect(screen.getByText('Bank Central Asia')).toBeInTheDocument()
    expect(screen.getByText('••••4821')).toBeInTheDocument()
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

    await waitFor(() => expect(apiBlob).toHaveBeenCalledWith('/api/documents/doc_img/pages/1?variant=full'))
    expect(apiBlob).not.toHaveBeenCalledWith('/api/documents/doc_img/pages/1?variant=thumb')
    expect(screen.getByText('Reading')).toBeInTheDocument()
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
      expect(screen.getByRole('heading', { name: 'To_Delete.pdf' })).toBeInTheDocument()
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

  it('lists the lines read a page at a time and points at a value on its page (T005-11)', async () => {
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
      reading: { method: 'AI_TEXT_LAYER', agreement: '1.000', fieldsCompared: 90, fieldsAgreed: 89, lines: 30 },
      statementMeta: {
        bankName: 'RHB Bank Berhad',
        accountMasked: '••••3876',
        currency: 'MYR',
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
    // 28 small debits of 0.10 (2.80 exactly, where floats drift), one credit, one line to check.
    const items = [
      ...Array.from({ length: 28 }, (_, i) => line(`tx_${i}`, 1, '-0.10', `DEBIT CARD TXN-DR\nSHOP ${i}`)),
      line('tx_in', 2, '250.00', 'MBK INSTANT TRF CR\nNURUL AINA'),
      line('tx_odd', 2, '-12.40', 'DEBIT CARD TXN-DR\nGRAB RIDES', 'CONFLICT'),
    ]
    vi.mocked(apiClient).mockImplementation(async (path: string) =>
      path.startsWith('/api/bank-lines') ? { items } : doc,
    )

    renderPage('doc_lines')

    await waitFor(() => expect(screen.getByText('1 to 25 of 30')).toBeInTheDocument())
    expect(screen.getByRole('tab', { name: /Transactions/ })).toHaveAttribute('aria-selected', 'true')
    expect(apiClient).toHaveBeenCalledWith('/api/bank-lines?docId=doc_lines')
    expect(screen.getByText('Read: 89 of 90 values found on the page')).toBeInTheDocument()
    expect(screen.getByText(/1,216\.73/)).toBeInTheDocument()
    expect(screen.getByText(/^\D*250\.00$/)).toBeInTheDocument() // money in
    expect(screen.getByText(/^\D*15\.20$/)).toBeInTheDocument() // money out: 2.80 + 12.40
    expect(screen.getByText('1 credit')).toBeInTheDocument()
    expect(screen.getByText('29 debits')).toBeInTheDocument()

    // A page of 25 lines, then the rest.
    expect(screen.queryByText('NURUL AINA')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Next' }))
    expect(screen.getByText('26 to 30 of 30')).toBeInTheDocument()
    expect(screen.getByText('NURUL AINA')).toBeInTheDocument()

    // To check: only the line whose readings differ, and it says why.
    fireEvent.click(screen.getByRole('button', { name: /To check/ }))
    expect(screen.getByText('1 to 1 of 1')).toBeInTheDocument()
    expect(screen.getByText(/page 2 · Readings differ/)).toBeInTheDocument()
    expect(screen.queryByTestId('page-lamp')).not.toBeInTheDocument()

    fireEvent.click(screen.getByText('DEBIT CARD TXN-DR'))

    await waitFor(() => expect(screen.getByTestId('page-lamp')).toBeInTheDocument())
    expect(apiBlob).toHaveBeenCalledWith('/api/documents/doc_lines/pages/2?variant=full')
    expect(screen.getByText('Page 2 of 2')).toBeInTheDocument()
    expect(screen.getByTestId('page-lamp').style.left).toBe('61.6%')
  })

  it('moves between pages and zooms the page (docs/11 §6.3)', async () => {
    vi.mocked(apiClient).mockResolvedValue({
      docId: 'doc_view',
      fileName: 'scan.pdf',
      contentType: 'application/pdf',
      docType: 'RECEIPT',
      status: 'DONE',
      pageCount: 3,
      pages: [1, 2, 3].map((pageNo) => ({ pageNo, status: 'DONE', textLayer: false, witness: 'OCR' })),
      uploadedAt: '2026-10-12T01:57:18Z',
    })
    renderPage('doc_view')

    await waitFor(() => expect(screen.getByText('Page 1 of 3')).toBeInTheDocument())
    expect(screen.getByText('Scanned')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Previous page' })).toBeDisabled()
    fireEvent.click(screen.getByRole('button', { name: 'Next page' }))
    fireEvent.click(screen.getByRole('button', { name: 'Next page' }))
    expect(screen.getByText('Page 3 of 3')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Next page' })).toBeDisabled()
    await waitFor(() => expect(apiBlob).toHaveBeenCalledWith('/api/documents/doc_view/pages/3?variant=full'))

    expect(screen.getByText('100%')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Zoom in' }))
    expect(screen.getByText('125%')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Zoom out' }))
    fireEvent.click(screen.getByRole('button', { name: 'Zoom out' }))
    expect(screen.getByText('75%')).toBeInTheDocument()
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
    expect(screen.getByRole('tab', { name: /Invoices/ })).toHaveAttribute('aria-selected', 'true')
    expect(screen.getByText('12 of 12 values found on the page')).toBeInTheDocument()
    expect(screen.getByText('Daybreak Café')).toBeInTheDocument()
    expect(screen.queryByTestId('page-lamp')).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /Total/ }))

    await waitFor(() => expect(screen.getByTestId('page-lamp')).toBeInTheDocument())
    expect(screen.getByTestId('page-lamp').style.left).toBe('69.6%')
  })

  it('shows the verdict and each finding with its facts, and lights its evidence (spec 006)', async () => {
    const box = { x0: 0.72, y0: 0.4, x1: 0.8, y1: 0.41 }
    vi.mocked(apiClient).mockImplementation(async (path: string) => {
      if (path.startsWith('/api/findings'))
        return {
          items: [
            {
              findingId: 'fnd_0000000000000001',
              code: 'A01_RUNNING_BALANCE_BREAK',
              category: 'ARITHMETIC',
              scope: 'DOCUMENT',
              severity: 'CRITICAL',
              title: 'The balance on 15 Mar does not follow from the last',
              facts: { row: '12', difference: '-6000000.00' },
              nextSteps: ['Ask the bank for the original statement.'],
              evidence: [{ docId: 'doc_t', page: 1, bbox: box, label: 'Printed balance' }],
              detectedBy: 'RULE',
              status: 'OPEN',
            },
            {
              findingId: 'fnd_0000000000000002',
              code: 'M01_EDITING_SOFTWARE_PRODUCER',
              category: 'STRUCTURE',
              scope: 'DOCUMENT',
              severity: 'MEDIUM',
              title: 'Old finding',
              facts: {},
              evidence: [],
              detectedBy: 'RULE',
              status: 'RESOLVED',
            },
          ],
        }
      if (path.startsWith('/api/bank-lines')) return { items: [] }
      return {
        docId: 'doc_t',
        fileName: 'edited.pdf',
        contentType: 'application/pdf',
        docType: 'BANK_STATEMENT',
        status: 'DONE',
        pageCount: 1,
        pages: [{ pageNo: 1, status: 'DONE', textLayer: true, witness: 'TEXT_LAYER' }],
        integrity: { verdict: 'TAMPERED' },
        uploadedAt: '2026-10-12T01:57:18Z',
      }
    })

    renderPage('doc_t')

    await waitFor(() => expect(screen.getByRole('tab', { name: /Findings/ })).toHaveTextContent('1'))
    expect(screen.getByText('Edited')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('tab', { name: /Findings/ }))
    expect(screen.getByText('The balance on 15 Mar does not follow from the last')).toBeInTheDocument()
    expect(screen.getByText('Critical')).toBeInTheDocument()
    expect(screen.getByText('-6000000.00')).toBeInTheDocument()
    expect(screen.getByText('Ask the bank for the original statement.')).toBeInTheDocument()
    expect(screen.queryByText('Old finding')).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Show on page 1' }))
    await waitFor(() => expect(screen.getByTestId('page-lamp')).toBeInTheDocument())
  })
})
