/**
 * A month's invoices and receipts with their payment evidence (spec 007, T007-10d, AC-007-12,
 * AC-007-14…16; ADR-025): each a chip of its own state, each opening its document.
 */

import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router-dom'
import { formatDate } from '../../shared/lib/formatDate'
import { formatAmount } from '../../shared/lib/formatMoney'
import { DataTable, type DataTableColumn, type DataTableFilter, Icon, type IconName } from '../../shared/ui'
import { type Payment, type Row, useMonthDocuments } from './useMonthDocuments'

const CHIP: Record<Payment, { chip: string; icon: IconName }> = {
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
const PAID: Payment[] = ['PAID_BANK', 'CONFIRMED_BY_YOU', 'PAID_CASH']

export function MonthDocuments({ month, currency }: { month: string; currency: string }) {
  const { t } = useTranslation('months')
  const navigate = useNavigate()
  const { rows: items, isLoading } = useMonthDocuments(month)
  const title = (r: Row) =>
    r.kind === 'RECEIPT'
      ? r.number
        ? t('monthDetail.docs.receipt', { number: r.number })
        : t('monthDetail.docs.receiptNoNumber')
      : r.number
        ? t('monthDetail.docs.invoice', { number: r.number })
        : t('monthDetail.docs.invoiceNoNumber')
  const who = (r: Row) => {
    const party = r.party || t('monthDetail.docs.unknownParty')
    if (r.kind === 'SALES') return t('monthDetail.docs.sales', { party })
    if (r.kind === 'PURCHASE') return t('monthDetail.docs.purchase', { party })
    return t('monthDetail.docs.merchant', { party })
  }
  const isPaid = (r: Row) => PAID.includes(r.payment)
  const filters: DataTableFilter<Row>[] = [
    { key: 'all', label: t('monthDetail.docs.filterAll'), predicate: () => true, count: items.length },
    { key: 'open', label: t('monthDetail.docs.filterOpen'), predicate: (r) => !isPaid(r), count: items.filter((r) => !isPaid(r)).length },
    { key: 'paid', label: t('monthDetail.docs.filterPaid'), predicate: isPaid, count: items.filter(isPaid).length },
  ]
  const columns: DataTableColumn<Row>[] = [
    {
      key: 'document',
      header: t('monthDetail.docs.colDocument'),
      wideOnMobile: true,
      sortable: true,
      sortValue: (r) => r.date ?? '',
      render: (r) => (
        <div>
          <strong>{title(r)}</strong>
          <div className="reason">{who(r)}</div>
          {r.date && <div className="reason">{formatDate(r.date)}</div>}
        </div>
      ),
    },
    {
      key: 'amount',
      header: t('monthDetail.docs.colAmount', { currency }),
      align: 'right',
      sortable: true,
      sortValue: (r) => Number(r.total?.amount ?? 0),
      render: (r) => (r.total ? formatAmount(r.total.amount, { currency: r.total.currency }) : '—'),
    },
    {
      key: 'payment',
      header: t('monthDetail.docs.colPayment'),
      wideOnMobile: true,
      render: (r) => (
        <span className={`match-chip ${CHIP[r.payment].chip}`}>
          <Icon name={CHIP[r.payment].icon} size="sm" />
          <span>{t(`monthDetail.payment.${r.payment}`)}</span>
        </span>
      ),
    },
  ]
  if (!isLoading && items.length === 0) {
    return (
      <div className="stack gap-3">
        <p className="muted">{t('monthDetail.docs.none')}</p>
        <Link className="button button-secondary button-sm self-start" to="/documents?upload=1">
          {t('monthDetail.docs.upload')}
        </Link>
      </div>
    )
  }
  return (
    <DataTable
      data={items}
      columns={columns}
      getRowKey={(r) => r.id}
      filters={filters}
      filterGroupAriaLabel={t('monthDetail.tabs.documents')}
      searchable
      searchPlaceholder={t('monthDetail.docs.search')}
      searchPredicate={(r, q) =>
        [r.number, r.party, r.date, r.total?.amount].filter(Boolean).some((text) => String(text).toLowerCase().includes(q))
      }
      isLoading={isLoading}
      onRowClick={(r) => navigate(`/documents/${r.docId}`)}
    />
  )
}
