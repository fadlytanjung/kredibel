/**
 * The bank lines behind a band or node of the money flow (spec 010, T010-05, AC-010-6): a sheet on
 * phones, a side panel from 600 px; each line opens its month's bank lines.
 */

import { useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { type FlowView, type Framework, useFlowLines } from '../../entities/insight'
import { formatDate } from '../../shared/lib/formatDate'
import { formatAmount } from '../../shared/lib/formatMoney'
import { Icon } from '../../shared/ui'
import { sumAmounts } from './units'

export interface FlowLinesSheetProps {
  flowId: string
  title: string
  period: string
  view: FlowView
  framework?: Framework
  onClose: () => void
}

export function FlowLinesSheet({ flowId, title, period, view, framework, onClose }: FlowLinesSheetProps) {
  const { t } = useTranslation('dashboard')
  const { data, isLoading } = useFlowLines(flowId, period, view, framework)
  const lines = data?.items ?? []
  const currency = lines[0]?.amount.currency ?? ''

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <div className="flow-sheet">
      <button type="button" className="scrim" aria-label={t('charts.sheet.close')} onClick={onClose} />
      <section className="sheet" role="dialog" aria-modal="true" aria-labelledby="flow-sheet-h">
        <div className="sheet-head">
          <div>
            <h2 id="flow-sheet-h">{title}</h2>
            <p className="muted small">
              {isLoading
                ? t('charts.sheet.loading')
                : t('charts.sheet.total', {
                    lines: t('charts.lines', { count: lines.length }),
                    total: formatAmount(sumAmounts(lines.map((l) => l.amount.amount)), { currency }),
                    currency,
                  })}
            </p>
          </div>
          <button type="button" className="icon-button" aria-label={t('charts.sheet.close')} onClick={onClose}>
            <Icon name="x" />
          </button>
        </div>
        <div className="sheet-body">
          {lines.map((line) => (
            <Link key={line.txId} className="line-row" to={`/months/${line.month}?tab=lines`}>
              <span>{line.description}</span>
              <span className="amt">{formatAmount(line.amount.amount, { currency })}</span>
              <span className="s">
                {formatDate(line.date)}
                {line.counterpartyName ? `, ${line.counterpartyName}` : ''}
              </span>
            </Link>
          ))}
        </div>
      </section>
    </div>
  )
}
