/**
 * Documents first (spec 007, T007-10c, AC-007-15, AC-007-16; ADR-025): every invoice and receipt
 * with its payment evidence. A document before its statement waits without an accusation; a person
 * can approve the document, or confirm its payment by hand, as two distinct audited decisions.
 */

import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useCreateDecision } from '../../entities/decision'
import { formatDate } from '../../shared/lib/formatDate'
import { formatAmount } from '../../shared/lib/formatMoney'
import { Badge, Button, DataTable, type DataTableColumn, type DataTableFilter, Icon } from '../../shared/ui'
import { PAID, PAYMENT_CHIP, type Payment, type Row, rowTitle, rowWho } from '../month'
import { PaymentSheet } from './PaymentSheet'

export function DocumentsFirstView({ rows, currency, isLoading }: { rows: Row[]; currency: string; isLoading: boolean }) {
  const { t } = useTranslation(['months', 'common'])
  const create = useCreateDecision()
  const [paying, setPaying] = useState<Row | null>(null)
  const [status, setStatus] = useState('')
  const sorted = [...rows].sort((a, b) => (b.date ?? '').localeCompare(a.date ?? '') || a.id.localeCompare(b.id))
  const groups: { key: string; label: string; of: Payment[] }[] = [
    { key: 'waiting', label: t('months:monthDetail.payment.WAITING_FOR_STATEMENT'), of: ['WAITING_FOR_STATEMENT', 'NOT_DUE'] },
    { key: 'nomatch', label: t('months:monthDetail.payment.NO_BANK_MATCH'), of: ['NO_BANK_MATCH', 'PROPOSED', 'PARTIAL_BANK'] },
    { key: 'unpaid', label: t('months:monthDetail.payment.UNPAID'), of: ['UNPAID'] },
    { key: 'paid', label: t('months:monthDetail.docs.filterPaid'), of: PAID },
  ]
  const filters: DataTableFilter<Row>[] = [
    { key: 'all', label: t('months:monthDetail.docs.filterAll'), predicate: () => true, count: sorted.length },
    ...groups.map((g) => ({
      key: g.key,
      label: g.label,
      predicate: (r: Row) => g.of.includes(r.payment),
      count: sorted.filter((r) => g.of.includes(r.payment)).length,
    })),
  ]
  const canConfirm = (r: Row) => !PAID.includes(r.payment) && r.payment !== 'CURRENCY_TO_CONFIRM'
  const approve = (r: Row) =>
    create.mutate(
      { kind: 'DOCUMENT_APPROVAL', docId: r.docId },
      { onSuccess: () => setStatus(t('months:all.docs.approvedStatus', { title: rowTitle(t, r) })) },
    )
  const columns: DataTableColumn<Row>[] = [
    {
      key: 'document',
      header: t('months:monthDetail.docs.colDocument'),
      wideOnMobile: true,
      sortable: true,
      sortValue: (r) => r.date ?? '',
      render: (r) => (
        <div>
          <strong>{rowTitle(t, r)}</strong>
          <div className="reason">{rowWho(t, r)}</div>
          {r.date && <div className="reason">{formatDate(r.date)}</div>}
          {r.noCurrencyPrinted && <div className="reason">{t('monthDetail.docs.noCurrencyPrinted', { currency })}</div>}
        </div>
      ),
    },
    {
      key: 'amount',
      header: t('months:monthDetail.docs.colAmount', { currency }),
      align: 'right',
      sortable: true,
      sortValue: (r) => Number(r.total?.amount ?? 0),
      render: (r) => (r.total ? formatAmount(r.total.amount, { currency: r.total.currency }) : '—'),
    },
    {
      key: 'payment',
      header: t('months:monthDetail.docs.colPayment'),
      wideOnMobile: true,
      render: (r) => (
        <div className="stack gap-1">
          <span className={`match-chip ${PAYMENT_CHIP[r.payment].chip}`}>
            <Icon name={PAYMENT_CHIP[r.payment].icon} size="sm" />
            <span>{t(`months:monthDetail.payment.${r.payment}`)}</span>
          </span>
          {r.approved && <Badge variant="clean">{t('months:all.docs.approved')}</Badge>}
        </div>
      ),
    },
    {
      key: 'actions',
      header: t('months:monthDetail.colActions'),
      align: 'right',
      render: (r) => (
        <div className="row gap-2 justify-end flex-wrap">
          {!r.approved && (
            <Button variant="secondary" size="sm" disabled={create.isPending} onClick={() => approve(r)}>
              {t('months:all.docs.approve')}
            </Button>
          )}
          {canConfirm(r) && (
            <Button variant="secondary" size="sm" onClick={() => setPaying(r)}>
              {t('months:all.docs.confirmPayment')}
            </Button>
          )}
        </div>
      ),
    },
  ]

  return (
    <section className="stack gap-4" aria-labelledby="documents-first-h">
      <h2 className="type-h2" id="documents-first-h">
        {t('months:all.docs.title')}
      </h2>
      <p className="muted">{t('months:all.docs.intro')}</p>
      {status && (
        <p className="muted" role="status">
          {status}
        </p>
      )}
      {!isLoading && sorted.length === 0 ? (
        <p className="muted">{t('months:all.docs.none')}</p>
      ) : (
        <DataTable
          data={sorted}
          columns={columns}
          getRowKey={(r) => r.id}
          filters={filters}
          filterGroupAriaLabel={t('months:all.docs.filterLabel')}
          searchable
          searchPlaceholder={t('months:monthDetail.docs.search')}
          searchPredicate={(r, q) =>
            [r.number, r.party, r.date, r.total?.amount].filter(Boolean).some((text) => String(text).toLowerCase().includes(q))
          }
          isLoading={isLoading}
          loadingMessage={<p className="muted">{t('months:all.loading')}</p>}
        />
      )}
      {paying && (
        <PaymentSheet
          row={paying}
          currency={currency}
          onClose={() => setPaying(null)}
          onConfirmed={() => {
            setStatus(t('months:all.pay.confirmedStatus', { title: rowTitle(t, paying) }))
            setPaying(null)
          }}
        />
      )}
    </section>
  )
}
