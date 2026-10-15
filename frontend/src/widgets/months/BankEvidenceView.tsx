/**
 * Bank evidence (spec 007, T007-10c, AC-007-14; ADR-025): every bank line of the workspace with
 * what supports it. A line without a document is bank cash all the same; it reads "No document
 * yet" and opens the match sheet to attach a document or say none is needed.
 */

import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import type { BankLine } from '../../entities/bank-line'
import { formatDate, formatMonth } from '../../shared/lib/formatDate'
import { formatAmount } from '../../shared/lib/formatMoney'
import { Button, DataTable, type DataTableColumn, type DataTableFilter, Icon } from '../../shared/ui'
import { MatchSheet, type Row } from '../month'
import { REASONED, type Support, SUPPORT_CHIP, supportOf } from './support'

export function BankEvidenceView({
  lines,
  documents,
  currency,
  isLoading,
}: {
  lines: BankLine[]
  documents: Row[]
  currency: string
  isLoading: boolean
}) {
  const { t } = useTranslation(['months', 'common'])
  const [matching, setMatching] = useState<BankLine | null>(null)
  const [status, setStatus] = useState('')
  const sorted = [...lines].sort((a, b) => (b.date ?? '').localeCompare(a.date ?? '') || a.txId.localeCompare(b.txId))
  const kinds: { key: string; label: string; of: Support[] }[] = [
    { key: 'none', label: t('months:monthDetail.support.NO_SUPPORT'), of: ['NO_SUPPORT'] },
    { key: 'proposed', label: t('months:monthDetail.support.PROPOSED'), of: ['PROPOSED'] },
    { key: 'matched', label: t('months:all.bank.filterMatched'), of: ['AUTO', 'MANUAL'] },
    { key: 'cleared', label: t('months:monthDetail.support.NOT_REQUIRED'), of: ['NOT_REQUIRED'] },
    { key: 'excluded', label: t('months:monthDetail.support.EXCLUDED'), of: ['EXCLUDED'] },
  ]
  const filters: DataTableFilter<BankLine>[] = [
    { key: 'all', label: t('months:monthDetail.filterAll'), predicate: () => true, count: sorted.length },
    ...kinds.map((k) => ({
      key: k.key,
      label: k.label,
      predicate: (l: BankLine) => k.of.includes(supportOf(l)),
      count: sorted.filter((l) => k.of.includes(supportOf(l))).length,
    })),
  ]
  const columns: DataTableColumn<BankLine>[] = [
    {
      key: 'line',
      header: t('months:monthDetail.colBankLine'),
      wideOnMobile: true,
      sortable: true,
      sortValue: (l) => l.date ?? '',
      render: (l) => (
        <div>
          <strong>{l.counterpartyName || l.description.split('\n')[0]}</strong>
          {l.date && <div className="reason">{formatDate(l.date)}</div>}
        </div>
      ),
    },
    {
      key: 'month',
      header: t('months:all.colMonth'),
      hideOnMobile: true,
      sortable: true,
      sortValue: (l) => l.month ?? '',
      render: (l) => (l.month ? formatMonth(l.month) : '—'),
    },
    {
      key: 'amount',
      header: t('months:monthDetail.colAmount', { currency }),
      align: 'right',
      sortable: true,
      sortValue: (l) => Number(l.amount?.amount ?? 0),
      render: (l) => {
        const v = l.amount?.amount ?? '0'
        const incoming = !v.startsWith('-')
        return (
          <span className={incoming ? 'amt-in' : 'amt-out'}>
            {incoming ? '+' : ''}
            {formatAmount(v, { currency })}
          </span>
        )
      },
    },
    {
      key: 'support',
      header: t('months:monthDetail.colMatchedWith'),
      wideOnMobile: true,
      render: (l) => {
        const k = supportOf(l)
        return (
          <div className="stack gap-1">
            <span className={`match-chip ${SUPPORT_CHIP[k].chip}`}>
              <Icon name={SUPPORT_CHIP[k].icon} size="sm" />
              <span>{t(`months:monthDetail.support.${k}`)}</span>
            </span>
            {REASONED.includes(k) && <span className="reason">{t(`months:monthDetail.supportReason.${k}`)}</span>}
          </div>
        )
      },
    },
    {
      key: 'actions',
      header: t('months:monthDetail.colActions'),
      align: 'right',
      render: (l) => {
        const k = supportOf(l)
        return k === 'NO_SUPPORT' || k === 'PROPOSED' ? (
          <Button variant="secondary" size="sm" onClick={() => setMatching(l)}>
            {t('months:monthDetail.match')}
          </Button>
        ) : null
      },
    },
  ]

  return (
    <section className="stack gap-4" aria-labelledby="bank-evidence-h">
      <h2 className="type-h2" id="bank-evidence-h">
        {t('months:all.bank.title')}
      </h2>
      <p className="muted">{t('months:all.bank.intro')}</p>
      {status && (
        <p className="muted" role="status">
          {status}
        </p>
      )}
      {!isLoading && sorted.length === 0 ? (
        <p className="muted">{t('months:all.bank.none')}</p>
      ) : (
        <DataTable
          data={sorted}
          columns={columns}
          getRowKey={(l) => l.txId}
          filters={filters}
          filterGroupAriaLabel={t('months:all.bank.filterLabel')}
          searchable
          searchPlaceholder={t('months:monthDetail.searchPlaceholder')}
          searchPredicate={(l, q) =>
            [l.description, l.counterpartyName ?? '', l.date ?? '', l.amount?.amount ?? ''].some((text) =>
              text.toLowerCase().includes(q),
            )
          }
          isLoading={isLoading}
          loadingMessage={<p className="muted">{t('months:monthDetail.loadingBankLines')}</p>}
        />
      )}
      {matching && (
        <MatchSheet
          line={matching}
          month={matching.month ?? ''}
          currency={currency}
          documents={documents.filter((d) => !matching.month || d.month === matching.month)}
          onClose={() => setMatching(null)}
          onMatched={(id) => {
            setStatus(t('months:monthDetail.matchedStatus', { id }))
            setMatching(null)
          }}
          onNotRequired={() => {
            setStatus(t('months:all.bank.notRequiredStatus'))
            setMatching(null)
          }}
        />
      )}
    </section>
  )
}
