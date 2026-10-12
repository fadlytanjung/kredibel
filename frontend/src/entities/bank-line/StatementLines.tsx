/**
 * One statement's lines as read: filtered, a page at a time, each amount marked with how it was
 * found (spec 005, T005-11; mock design/mocks/document.html).
 */

import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { formatDate } from '../../shared/lib/formatDate'
import { formatMoney } from '../../shared/lib/formatMoney'
import { Button } from '../../shared/ui'
import type { BankLine } from './api'
import { isIncoming, lineStatus, needsCheck } from './lines'

type Filter = 'all' | 'in' | 'out' | 'check'

const PAGE_SIZE = 25
const FILTERS: Filter[] = ['all', 'in', 'out', 'check']
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
  const { t } = useTranslation('documents')
  const [filter, setFilter] = useState<Filter>('all')
  const [start, setStart] = useState(0)
  const shown = lines.filter(KEEP[filter])
  const page = shown.slice(start, start + PAGE_SIZE)
  const choose = (next: Filter) => {
    setFilter(next)
    setStart(0)
  }

  return (
    <div className="stack gap-3">
      <div className="chips" role="group" aria-label={t('detail.lines.filter')}>
        {FILTERS.map((key) => (
          <button key={key} type="button" className="chip" aria-pressed={filter === key} onClick={() => choose(key)}>
            {t(`detail.lines.${key}`)} <span className="n">{lines.filter(KEEP[key]).length}</span>
          </button>
        ))}
      </div>

      {page.length === 0 ? (
        <p className="muted small">{t('detail.lines.none')}</p>
      ) : (
        <div className="table-panel rt-wrap">
          <table className="data-table rt">
            <thead>
              <tr>
                <th>{t('detail.columns.transaction')}</th>
                <th className="r">{t('detail.columns.amount')}</th>
              </tr>
            </thead>
            <tbody>
              {page.map((line) => {
                const status = lineStatus(line)
                const amountStatus = line.readings?.amount?.status ?? status
                const incoming = isIncoming(line)
                const [first, ...rest] = line.description.split('\n')
                const detail = line.counterpartyName ? line.description.replace(/\n/g, ' · ') : rest.join(' · ')
                const where = t('detail.lines.where', { date: formatDate(line.date), page: line.page })
                const check =
                  line.source === 'WITNESS' ? t('detail.witnessRow') : status !== 'AGREED' ? t(`detail.readingStatus.${status}`) : ''
                return (
                  <tr
                    key={line.txId}
                    className={`is-clickable ${line.txId === selectedTxId ? 'is-selected' : ''}`}
                    aria-selected={line.txId === selectedTxId}
                    tabIndex={0}
                    onClick={() => onSelect(line)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault()
                        onSelect(line)
                      }
                    }}
                  >
                    <td>
                      <strong className="block">{line.counterpartyName || first}</strong>
                      {detail && <div className="reason">{detail}</div>}
                      <div className="reason">{check ? `${where} · ${check}` : where}</div>
                    </td>
                    <td className="r">
                      <span className={incoming ? 'amt-in' : 'amt-out'}>
                        <span className={`reading ${line.source === 'WITNESS' ? MARK.SINGLE_SOURCE : MARK[amountStatus]}`}>
                          {incoming ? '+' : ''}
                          {formatMoney(line.amount.amount, { currency: line.amount.currency })}
                        </span>
                      </span>
                      <span className="sr-only">{t(`detail.readingStatus.${amountStatus}`)}</span>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {shown.length > 0 && (
        <div className="pager-line">
          <span>
            {t('detail.lines.range', { from: start + 1, to: Math.min(start + PAGE_SIZE, shown.length), total: shown.length })}
          </span>
          {shown.length > PAGE_SIZE && (
            <span className="row">
              <Button variant="secondary" size="sm" disabled={start === 0} onClick={() => setStart(start - PAGE_SIZE)}>
                {t('detail.lines.previous')}
              </Button>
              <Button
                variant="secondary"
                size="sm"
                disabled={start + PAGE_SIZE >= shown.length}
                onClick={() => setStart(start + PAGE_SIZE)}
              >
                {t('detail.lines.next')}
              </Button>
            </span>
          )}
        </div>
      )}

      <p className="reading-legend">
        <span>
          <span className="reading reading-agreed">{t('detail.legend.sample')}</span> {t('detail.legend.agreed')}
        </span>
        <span>
          <span className="reading reading-single">{t('detail.legend.sample')}</span> {t('detail.legend.single')}
        </span>
        <span>
          <span className="reading reading-conflict">{t('detail.legend.sample')}</span> {t('detail.legend.conflict')}
        </span>
      </p>
    </div>
  )
}
