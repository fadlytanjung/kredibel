/**
 * One dashboard figure (spec 010, T010-04, AC-010-1): money in the workspace currency printed
 * once, the automatic match rate, or a count, with the previous period of equal length.
 */

import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import type { Kpi } from '../../entities/insight'
import { formatAmount } from '../../shared/lib/formatMoney'
import { Icon, type IconName } from '../../shared/ui'

type Money = { amount: string; currency: string }

function isMoney(value: unknown): value is Money {
  return typeof value === 'object' && value !== null && 'amount' in value
}

function percent(rate: string): string {
  return `${(Math.round(Number(rate) * 1000) / 10).toFixed(1)}%`
}

const ICON: Partial<Record<Kpi['id'], IconName>> = { MONEY_IN: 'arrow-down-left', MONEY_OUT: 'arrow-up-right' }

export function KpiCard({ kpi }: { kpi: Kpi }) {
  const { t } = useTranslation('dashboard')
  const { value, previous } = kpi
  const shown = (v: unknown, signed = false) => {
    if (isMoney(v)) {
      const sign = signed && !v.amount.startsWith('-') && v.amount !== '0.00' ? '+' : ''
      return `${sign}${formatAmount(v.amount, { currency: v.currency })}`
    }
    if (kpi.id === 'AUTO_MATCH_RATE' && typeof v === 'string') return percent(v)
    return String(v)
  }
  const signed = kpi.id === 'NET'
  const icon = ICON[kpi.id]
  let note: ReactNode
  if (kpi.id === 'DOCUMENTS_WAITING') {
    const count = Number(value)
    note = count ? (
      <Link className="link" to="/documents?filter=duplicates">
        {t('documentsWaiting', { count })}
      </Link>
    ) : (
      t('nothingWaiting')
    )
  } else if (kpi.id === 'NET' && isMoney(value)) {
    note = value.amount.startsWith('-') ? t('taken') : t('kept')
  } else {
    note = previous !== null && previous !== undefined ? t('previous', { value: shown(previous, signed) }) : t('noPrevious')
  }
  return (
    <div className={kpi.id === 'DOCUMENTS_WAITING' && Number(value) > 0 ? 'is-attn' : undefined}>
      <dt>
        {icon && <Icon name={icon} size="sm" />}
        {t(`kpi.${kpi.id}`)}
      </dt>
      <dd className="v">
        {isMoney(value) && <small>{value.currency}</small>}
        {shown(value, signed)}
      </dd>
      <dd className={`n${kpi.id === 'NET' && isMoney(value) && !value.amount.startsWith('-') ? ' up' : ''}`}>{note}</dd>
      {kpi.id === 'AUTO_MATCH_RATE' && typeof value === 'string' && (
        <dd className="mini">
          <i style={{ width: percent(value) }} /* allow-raw-style: the period's automatic match rate */ />
        </dd>
      )}
    </div>
  )
}
