/**
 * Slide-over drawer listing the ledger entries behind a node or band in Profit & Loss.
 * Allows drilling down into supporting subledger rows, accounts, amounts, and source documents.
 */

import { useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import type { ProfitLoss } from '../../entities/profit-loss'
import { formatDate } from '../../shared/lib/formatDate'
import { formatMoney } from '../../shared/lib/formatMoney'
import { Icon } from '../../shared/ui'

export type ProfitEntryItem = NonNullable<ProfitLoss['entries']>[number]

export interface ProfitLossEntriesSheetProps {
  title: string
  subtitle?: string
  currency: string
  entries: ProfitEntryItem[]
  onClose: () => void
}

export function ProfitLossEntriesSheet({
  title,
  subtitle,
  currency,
  entries,
  onClose,
}: ProfitLossEntriesSheetProps) {
  const { t } = useTranslation('profitLoss')

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [onClose])

  const totalAmount = entries.reduce((acc, e) => acc + (Number(e.amount) || 0), 0)

  return (
    <div className="flow-sheet">
      <button
        type="button"
        className="scrim"
        aria-label={t('entriesSheet.close', { defaultValue: 'Close entries' })}
        onClick={onClose}
      />
      <section className="sheet" role="dialog" aria-modal="true" aria-labelledby="pnl-sheet-h">
        <div className="sheet-head">
          <div>
            <h2 id="pnl-sheet-h">{title}</h2>
            {subtitle && <p className="text-xs text-muted mb-1">{subtitle}</p>}
            <p className="muted small">
              {t('entriesSheet.total', {
                count: entries.length,
                total: formatMoney(String(totalAmount), { currency, code: true }),
                currency,
                defaultValue: `${entries.length} entries · Total ${formatMoney(String(totalAmount), { currency, code: true })}`,
              })}
            </p>
          </div>
          <button
            type="button"
            className="icon-button"
            aria-label={t('entriesSheet.close', { defaultValue: 'Close entries' })}
            onClick={onClose}
          >
            <Icon name="x" />
          </button>
        </div>
        <div className="sheet-body">
          {entries.length === 0 ? (
            <p className="muted p-4">
              {t('entriesSheet.noEntries', { defaultValue: 'No entries found for this selection.' })}
            </p>
          ) : (
            entries.map((entry) => (
              <Link
                key={entry.entryId}
                className="line-row"
                to={`/documents/${entry.docId}`}
                title={`Row ${entry.rowNumber} · Document ${entry.docId}`}
              >
                <div>
                  <div className="font-semibold text-ink">
                    <span className="font-mono text-xs opacity-75 mr-1.5">{entry.accountCode}</span>
                    <span>{entry.accountName}</span>
                  </div>
                  <div className="text-xs text-muted mt-0.5 flex items-center gap-2">
                    <span className="badge badge-outline text-2xs py-0.5">
                      {t(`subledgers.${entry.subledger}`, { defaultValue: entry.subledger })}
                    </span>
                    <span>{formatDate(entry.date)}</span>
                    <span className="opacity-70">
                      {t('entriesSheet.row', { row: entry.rowNumber })}
                    </span>
                  </div>
                </div>
                <div className="text-right">
                  <span className="amt font-medium">
                    {formatMoney(entry.amount, { currency, code: true })}
                  </span>
                  <div className="text-xs text-muted font-mono mt-0.5 flex items-center justify-end gap-1">
                    <span>{entry.docId.slice(0, 10)}</span>
                    <Icon name="arrow-up-right" size="sm" />
                  </div>
                </div>
              </Link>
            ))
          )}
        </div>
      </section>
    </div>
  )
}
