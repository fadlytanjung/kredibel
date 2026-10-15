/** How a row of invoices and receipts is named on screen (shared by the month and all-months views). */

import type { TFunction } from 'i18next'
import type { IconName } from '../../shared/ui'
import type { Payment, Row } from './useMonthDocuments'

export const PAYMENT_CHIP: Record<Payment, { chip: string; icon: IconName }> = {
  PAID_BANK: { chip: 'auto', icon: 'link' },
  PARTIAL_BANK: { chip: 'proposed', icon: 'link' },
  PROPOSED: { chip: 'proposed', icon: 'eye' },
  CONFIRMED_BY_YOU: { chip: 'manual', icon: 'hand' },
  PAID_CASH: { chip: 'cleared', icon: 'wallet' },
  WAITING_FOR_STATEMENT: { chip: 'none', icon: 'clock' },
  NO_BANK_MATCH: { chip: 'none', icon: 'unlink' },
  NOT_DUE: { chip: 'excluded', icon: 'calendar' },
  UNPAID: { chip: 'overdue', icon: 'circle-alert' },
  CURRENCY_TO_CONFIRM: { chip: 'proposed', icon: 'globe' },
  NOT_RUN: { chip: 'none', icon: 'clock' },
}

/** Payment evidence that settles the document (ADR-025). */
export const PAID: Payment[] = ['PAID_BANK', 'CONFIRMED_BY_YOU', 'PAID_CASH']

export function rowTitle(t: TFunction, r: Row): string {
  if (r.kind === 'RECEIPT') {
    return r.number ? t('monthDetail.docs.receipt', { number: r.number }) : t('monthDetail.docs.receiptNoNumber')
  }
  return r.number ? t('monthDetail.docs.invoice', { number: r.number }) : t('monthDetail.docs.invoiceNoNumber')
}

export function rowWho(t: TFunction, r: Row): string {
  const party = r.party || t('monthDetail.docs.unknownParty')
  if (r.kind === 'SALES') return t('monthDetail.docs.sales', { party })
  if (r.kind === 'PURCHASE') return t('monthDetail.docs.purchase', { party })
  return t('monthDetail.docs.merchant', { party })
}
