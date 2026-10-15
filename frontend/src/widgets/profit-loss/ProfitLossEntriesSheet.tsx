/**
 * Slide-over drawer listing the ledger entries behind a node or band in Profit & Loss.
 * Allows drilling down into supporting subledger rows, accounts, amounts, and source documents.
 */

import { useEffect, useRef } from 'react'
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
  basis?: 'ACCRUAL' | 'CASH'
}

export function ProfitLossEntriesSheet({
  title,
  subtitle,
  currency,
  entries,
  onClose,
  basis = 'ACCRUAL',
}: ProfitLossEntriesSheetProps) {
  const { t } = useTranslation('profitLoss')
  const dialog = useRef<HTMLElement>(null)

  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null
    const focusable = () => Array.from(dialog.current?.querySelectorAll<HTMLElement>('button, a[href]') ?? [])
    focusable()[0]?.focus()
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
      if (e.key !== 'Tab') return
      const items = focusable()
      const next = e.shiftKey ? items.at(-1) : items[0]
      if (document.activeElement === (e.shiftKey ? items[0] : items.at(-1))) {
        e.preventDefault()
        next?.focus()
      }
    }
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('keydown', onKey)
      previous?.focus()
    }
  }, [onClose])


  return (
    <div className="flow-sheet">
      <button
        type="button"
        className="scrim"
        aria-label={t('entriesSheet.close', { defaultValue: 'Close entries' })}
        onClick={onClose}
      />
      <section ref={dialog} className="sheet" role="dialog" aria-modal="true" aria-labelledby="pnl-sheet-h">
        <div className="sheet-head">
          <div>
            <h2 id="pnl-sheet-h">{title}</h2>
            {subtitle && <p className="text-xs text-muted mb-1">{subtitle}</p>}
            <p className="muted small">
              {t('entriesSheet.count', { count: entries.length })}
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
                title={t('entriesSheet.row', { row: entry.rowNumber })}
              >
                <div>
                  <div className="font-semibold text-ink">
                    {basis !== 'CASH' && <span className="font-mono text-xs opacity-75 mr-1.5">{entry.accountCode}</span>}
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
