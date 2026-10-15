/**
 * One statement's lines as read: filtered, searchable, a page at a time, each amount marked with how it was
 * found (spec 005, T005-11; mock design/mocks/document.html).
 */

import { useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { formatDate } from '../../shared/lib/formatDate'
import { formatMoney } from '../../shared/lib/formatMoney'
import { DataTable, type DataTableColumn, type DataTableFilter } from '../../shared/ui'
import type { BankLine } from './api'
import { isIncoming, lineStatus, needsCheck } from './lines'

type Filter = 'all' | 'in' | 'out' | 'check'

const MARK = {
  AGREED: 'reading-agreed',
  SINGLE_SOURCE: 'reading-single',
  CONFLICT: 'reading-conflict',
  MISSING: 'reading-conflict',
} as const

const KEEP: Record<Filter, (line: BankLine) => boolean> = {
  all: () => true,
  in: isIncoming,
  out: (line) => !isIncoming(line),
  check: needsCheck,
}

interface StatementLinesProps {
  lines: BankLine[]
  selectedTxId?: string
  onSelect: (line: BankLine) => void
}

export function StatementLines({ lines, selectedTxId, onSelect }: StatementLinesProps) {
  const { t } = useTranslation(['documents', 'common'])

  const filters: DataTableFilter<BankLine>[] = useMemo(
    () => [
      { key: 'all', label: t('documents:detail.lines.all'), predicate: KEEP.all },
      { key: 'in', label: t('documents:detail.lines.in'), predicate: KEEP.in },
      { key: 'out', label: t('documents:detail.lines.out'), predicate: KEEP.out },
      { key: 'check', label: t('documents:detail.lines.check'), predicate: KEEP.check },
    ],
    [t],
  )

  const columns: DataTableColumn<BankLine>[] = useMemo(
    () => [
      {
        key: 'transaction',
        header: t('documents:detail.columns.transaction'),
        wideOnMobile: true,
        sortable: true,
        sortValue: (line) => line.counterpartyName || line.description,
        render: (line) => {
          const status = lineStatus(line)
          const [first, ...rest] = line.description.split('\n')
          const detail = line.counterpartyName ? line.description.replace(/\n/g, ' · ') : rest.join(' · ')
          const where = t('documents:detail.lines.where', { date: formatDate(line.date), page: line.page })
          const check =
            line.source === 'WITNESS'
              ? t('documents:detail.witnessRow')
              : status !== 'AGREED'
                ? t(`documents:detail.readingStatus.${status}`)
                : ''
          return (
            <div>
              <strong className="block">{line.counterpartyName || first}</strong>
              {detail && <div className="reason">{detail}</div>}
              <div className="reason">{check ? `${where} · ${check}` : where}</div>
            </div>
          )
        },
      },
      {
        key: 'amount',
        header: t('documents:detail.columns.amount'),
        align: 'right',
        sortable: true,
        sortValue: (line) => Number(line.amount.amount),
        render: (line) => {
          const status = lineStatus(line)
          const amountStatus = line.readings?.amount?.status ?? status
          const incoming = isIncoming(line)
          return (
            <>
              <span className={incoming ? 'amt-in' : 'amt-out'}>
                <span className={`reading ${line.source === 'WITNESS' ? MARK.SINGLE_SOURCE : MARK[amountStatus]}`}>
                  {incoming ? '+' : ''}
                  {formatMoney(line.amount.amount, { currency: line.amount.currency })}
                </span>
              </span>
              <span className="sr-only">{t(`documents:detail.readingStatus.${amountStatus}`)}</span>
            </>
          )
        },
      },
    ],
    [t],
  )

  const searchPredicate = (line: BankLine, q: string) => {
    if (line.counterpartyName && line.counterpartyName.toLowerCase().includes(q)) return true
    if (line.description && line.description.toLowerCase().includes(q)) return true
    if (line.date && line.date.includes(q)) return true
    if (line.amount?.amount && line.amount.amount.includes(q)) return true
    return false
  }

  return (
    <DataTable
      data={lines}
      columns={columns}
      getRowKey={(line) => line.txId}
      filters={filters}
      filterGroupAriaLabel={t('documents:detail.lines.filter')}
      searchable={true}
      searchPlaceholder={t('common:table.searchPlaceholder', { defaultValue: 'Search transactions...' })}
      searchPredicate={searchPredicate}
      rangeLabel={(from, to, total) =>
        t('documents:detail.lines.range', { from, to, total })
      }
      emptyMessage={<p className="muted small">{t('documents:detail.lines.none')}</p>}
      selectedRowKey={selectedTxId}
      onRowClick={onSelect}
      footer={
        <p className="reading-legend">
          <span>
            <span className="reading reading-agreed">{t('documents:detail.legend.sample')}</span>{' '}
            {t('documents:detail.legend.agreed')}
          </span>
          <span>
            <span className="reading reading-single">{t('documents:detail.legend.sample')}</span>{' '}
            {t('documents:detail.legend.single')}
          </span>
          <span>
            <span className="reading reading-conflict">{t('documents:detail.legend.sample')}</span>{' '}
            {t('documents:detail.legend.conflict')}
          </span>
        </p>
      }
    />
  )
}
