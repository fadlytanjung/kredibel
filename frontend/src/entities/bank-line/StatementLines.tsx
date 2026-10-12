/** One statement's lines as read, each with how its values were found (spec 005, T005-11). */

import { useTranslation } from 'react-i18next'
import { formatDate } from '../../shared/lib/formatDate'
import { formatMoney } from '../../shared/lib/formatMoney'
import { Badge } from '../../shared/ui'
import type { BankLine, ValueReading } from './api'

type Status = ValueReading['status']

const RANK: Record<string, number> = { AGREED: 0, SINGLE_SOURCE: 1, CONFLICT: 2, MISSING: 3 }
const VARIANT = { AGREED: 'clean', SINGLE_SOURCE: 'medium', CONFLICT: 'high', MISSING: 'critical' } as const

/** The weakest reading among a line's values decides its badge. */
export function lineStatus(line: BankLine): Status {
  const statuses = Object.values(line.readings ?? {}).map((r) => r.status)
  return statuses.reduce<Status>((worst, s) => ((RANK[s] ?? 0) > (RANK[worst] ?? 0) ? s : worst), 'AGREED')
}

/** Where to point on the page: the amount's box, else the description's. */
export function lineBox(line: BankLine) {
  return line.readings?.amount?.bbox ?? line.readings?.description?.bbox
}

interface StatementLinesProps {
  lines: BankLine[]
  selectedTxId?: string
  onSelect: (line: BankLine) => void
}

export function StatementLines({ lines, selectedTxId, onSelect }: StatementLinesProps) {
  const { t } = useTranslation('documents')
  return (
    <div className="table-panel rt-wrap">
      <table className="data-table rt">
        <thead>
          <tr>
            <th>{t('detail.columns.date')}</th>
            <th>{t('detail.columns.description')}</th>
            <th className="r">{t('detail.columns.amount')}</th>
            <th className="r">{t('detail.columns.balance')}</th>
            <th>{t('detail.columns.reading')}</th>
          </tr>
        </thead>
        <tbody>
          {lines.map((line) => {
            const status = lineStatus(line)
            const incoming = !line.amount.amount.startsWith('-')
            const [first, ...rest] = line.description.split('\n')
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
                <td className="whitespace-nowrap">{formatDate(line.date)}</td>
                <td data-cell="wide">
                  <strong className="block">{line.counterpartyName || first}</strong>
                  <span className="small muted">{line.counterpartyName ? line.description.replace(/\n/g, ' · ') : rest.join(' · ')}</span>
                </td>
                <td className={`r ${incoming ? 'amt-in' : 'amt-out'}`}>
                  {formatMoney(line.amount.amount, { currency: line.amount.currency })}
                </td>
                <td className="r">
                  {line.balance ? formatMoney(line.balance.amount, { currency: line.balance.currency }) : '—'}
                </td>
                <td>
                  <Badge variant={VARIANT[status]}>
                    {line.source === 'WITNESS' ? t('detail.witnessRow') : t(`detail.readingStatus.${status}`)}
                  </Badge>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
