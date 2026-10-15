/**
 * A month's invoices and receipts with their payment evidence (spec 007, T007-10d, AC-007-12,
 * AC-007-14…16; ADR-025): each a chip of its own state, each opening its document.
 */

import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router-dom'
import { formatDate } from '../../shared/lib/formatDate'
import { formatAmount } from '../../shared/lib/formatMoney'
import { DataTable, type DataTableColumn, type DataTableFilter, Icon } from '../../shared/ui'
import { PAID, PAYMENT_CHIP, rowTitle, rowWho } from './rowWords'
import { type Row, useMonthDocuments } from './useMonthDocuments'


export function MonthDocuments({ month, currency }: { month: string; currency: string }) {
  const { t } = useTranslation('months')
  const navigate = useNavigate()
  const { rows: items, isLoading } = useMonthDocuments(month)
  const title = (r: Row) => rowTitle(t, r)
  const who = (r: Row) => rowWho(t, r)
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
          {r.noCurrencyPrinted && <div className="reason">{t('monthDetail.docs.noCurrencyPrinted', { currency })}</div>}
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
        <span className={`match-chip ${PAYMENT_CHIP[r.payment].chip}`}>
          <Icon name={PAYMENT_CHIP[r.payment].icon} size="sm" />
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
