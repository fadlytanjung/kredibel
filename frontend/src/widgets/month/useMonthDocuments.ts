/** Invoices and receipts as one list of rows with their payment evidence (T007-10d, T007-10c). */

import {
  type Invoice,
  type Receipt,
  useAllInvoices,
  useAllReceipts,
  useMonthInvoices,
  useMonthReceipts,
} from '../../entities/record'

export type Payment = NonNullable<Invoice['evidence']>['payment'] | 'NOT_RUN'

export interface Row {
  id: string
  docId: string
  kind: 'SALES' | 'PURCHASE' | 'RECEIPT'
  number?: string | null
  party?: string | null
  date?: string | null
  month?: string | null
  total?: { amount: string; currency: string } | null
  outstanding?: { amount: string; currency: string } | null
  payment: Payment
  // Read in the workspace currency because the document prints none (ADR-025, T007-12).
  noCurrencyPrinted: boolean
  printedCurrency: string | null
  approved: boolean
}

export function rowsOf(invoices: Invoice[], receipts: Receipt[]): Row[] {
  return [
    ...invoices.map((i) => ({
      id: i.invoiceId,
      docId: i.docId,
      kind: i.kind,
      number: i.number,
      party: i.kind === 'SALES' ? i.buyerName : i.issuerName,
      date: i.issueDate,
      month: i.month,
      total: i.total,
      outstanding: i.evidence?.outstanding ?? null,
      payment: (i.evidence?.payment ?? 'NOT_RUN') as Payment,
      noCurrencyPrinted: !!i.evidence && !i.evidence.printedCurrency,
      printedCurrency: i.evidence?.printedCurrency ?? null,
      approved: Boolean(i.evidence?.approved),
    })),
    ...receipts.map((r) => ({
      id: r.receiptId,
      docId: r.docId,
      kind: 'RECEIPT' as const,
      number: r.number,
      party: r.merchantName,
      date: r.date,
      month: r.month,
      total: r.total,
      outstanding: r.evidence?.outstanding ?? null,
      payment: (r.evidence?.payment ?? 'NOT_RUN') as Payment,
      noCurrencyPrinted: !!r.evidence && !r.evidence.printedCurrency,
      printedCurrency: r.evidence?.printedCurrency ?? null,
      approved: Boolean(r.evidence?.approved),
    })),
  ].sort((a, b) => (a.date ?? '').localeCompare(b.date ?? '') || a.id.localeCompare(b.id))
}

export function useMonthDocuments(month: string) {
  const invoices = useMonthInvoices(month)
  const receipts = useMonthReceipts(month)
  return {
    rows: rowsOf(invoices.data?.items ?? [], receipts.data?.items ?? []),
    isLoading: invoices.isLoading || receipts.isLoading,
  }
}

/** Every invoice and receipt of the workspace (the all-months views, T007-10c). */
export function useAllDocuments(enabled = true) {
  const invoices = useAllInvoices(enabled)
  const receipts = useAllReceipts(enabled)
  return {
    rows: rowsOf(invoices.data?.items ?? [], receipts.data?.items ?? []),
    isLoading: enabled && (invoices.isLoading || receipts.isLoading),
  }
}
