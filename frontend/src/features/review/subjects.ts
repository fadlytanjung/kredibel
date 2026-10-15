/**
 * What an item is about, looked up in its month's records (the month page loads the same lists),
 * and the bank lines that could pay an unpaid document (docs/11 §6.5).
 */

import type { BankLine } from '../../entities/bank-line'
import type { Invoice, Receipt } from '../../entities/record'
import type { ReviewItem } from '../../entities/review'

export interface Subjects {
  lines: BankLine[]
  invoices: Invoice[]
  receipts: Receipt[]
}

export function subjectsOf(item: ReviewItem, month: Subjects): Subjects {
  const ids = item.subject
  return {
    lines: month.lines.filter((l) => ids.bankLineIds?.includes(l.txId)),
    invoices: month.invoices.filter((i) => ids.invoiceIds?.includes(i.invoiceId)),
    receipts: month.receipts.filter((r) => ids.receiptIds?.includes(r.receiptId)),
  }
}

const MAX_CANDIDATES = 3

/** Unmatched lines of the right direction, closest amount first: a sales invoice is paid in, a
 * purchase or a receipt is paid out. Only a short list; the person can still match from the month. */
export function linesThatCouldPay(document: Invoice | Receipt, lines: BankLine[]): BankLine[] {
  const total = Number(document.total?.amount ?? 0)
  if (!total) return []
  const paidIn = 'kind' in document && document.kind === 'SALES'
  return lines
    .filter((l) => (l.support === 'NO_SUPPORT' || !l.support) && !l.heldAsDuplicate)
    .filter((l) => (Number(l.amount.amount) > 0) === paidIn)
    .map((l) => ({ line: l, gap: Math.abs(Math.abs(Number(l.amount.amount)) - total) / total }))
    .filter((c) => c.gap <= 0.1)
    .sort((a, b) => a.gap - b.gap || a.line.date.localeCompare(b.line.date))
    .slice(0, MAX_CANDIDATES)
    .map((c) => c.line)
}
