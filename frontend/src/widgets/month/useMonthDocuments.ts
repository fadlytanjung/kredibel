/** A month's invoices and receipts as one list of rows with their payment evidence (T007-10d). */

import { type Invoice, type Receipt, useMonthInvoices, useMonthReceipts } from '../../entities/record'

export type Payment = NonNullable<Invoice['evidence']>['payment'] | 'NOT_RUN'

export interface Row {
  id: string
  docId: string
  kind: 'SALES' | 'PURCHASE' | 'RECEIPT'
  number?: string | null
  party?: string | null
  date?: string | null
  total?: { amount: string; currency: string } | null
  payment: Payment
}

function rows(invoices: Invoice[], receipts: Receipt[]): Row[] {
  return [
    ...invoices.map((i) => ({
      id: i.invoiceId,
      docId: i.docId,
      kind: i.kind,
      number: i.number,
      party: i.kind === 'SALES' ? i.buyerName : i.issuerName,
      date: i.issueDate,
      total: i.total,
      payment: (i.evidence?.payment ?? 'NOT_RUN') as Payment,
    })),
    ...receipts.map((r) => ({
      id: r.receiptId,
      docId: r.docId,
      kind: 'RECEIPT' as const,
      number: r.number,
      party: r.merchantName,
      date: r.date,
      total: r.total,
      payment: (r.evidence?.payment ?? 'NOT_RUN') as Payment,
    })),
  ].sort((a, b) => (a.date ?? '').localeCompare(b.date ?? '') || a.id.localeCompare(b.id))
}

export function useMonthDocuments(month: string) {
  const invoices = useMonthInvoices(month)
  const receipts = useMonthReceipts(month)
  return {
    rows: rows(invoices.data?.items ?? [], receipts.data?.items ?? []),
    isLoading: invoices.isLoading || receipts.isLoading,
  }
}

