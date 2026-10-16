/**
 * Spec 024, AC-024-5: what the person expected for each month against what the reconciled books
 * show, with the way to the month, its transactions and its documents. The expectation may be
 * wrong; the panel only compares.
 */
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { useExpectations, type ExpectationSide } from '../../entities/expectations'
import { formatMonth } from '../../shared/lib/formatDate'
import { formatAmount } from '../../shared/lib/formatMoney'
import { Icon } from '../../shared/ui'

const STATUS_ICON = { AS_EXPECTED: 'check-circle', DIFFERENT: 'scale', WAITING: 'clock' } as const
const STATUS_CLASS = { AS_EXPECTED: 'ok', DIFFERENT: 'wait', WAITING: 'busy' } as const

function Side({ label, side, currency }: { label: string; side: ExpectationSide; currency: string }) {
  const { t } = useTranslation('dashboard')
  const money = (amount: string) => formatAmount(amount, { currency })
  const difference = side.difference ?? '0'
  const status =
    side.status === 'DIFFERENT'
      ? t(difference.startsWith('-') ? 'expectations.status.DIFFERENT_less' : 'expectations.status.DIFFERENT_more', { difference: money(difference.replace(/^-/, '')) })
      : t(`expectations.status.${side.status}`)
  return (
    <div className="expect-side">
      <span className="k">{label}</span>
      <span className="v">
        <span>
          {t('expectations.expected')} <strong>{money(side.expected)}</strong>
        </span>
        {side.actual != null && (
          <span>
            {t('expectations.found')} <strong>{money(side.actual)}</strong>
          </span>
        )}
      </span>
      <span className={`status-line ${STATUS_CLASS[side.status]}`}>
        <Icon name={STATUS_ICON[side.status]} size="sm" />
        {status}
      </span>
    </div>
  )
}

export function ExpectationsPanel({ currency }: { currency: string }) {
  const { t } = useTranslation('dashboard')
  const { data } = useExpectations()
  if (!data || data.months.length === 0) return null
  const tolerance = Math.round(Number(data.tolerance) * 100)
  return (
    <section className="panel" aria-labelledby="dash-expect-h">
      <div className="panel-head">
        <div className="stack gap-1">
          <h2 id="dash-expect-h">{t('expectations.title')}</h2>
          <p className="small muted">{t('expectations.subtitle', { currency, tolerance })}</p>
        </div>
        <Link className="link" to="/welcome?expect=1">
          {t('expectations.change')}
        </Link>
      </div>
      <ul className="expect-list">
        {data.months.map((m) => (
          <li key={m.month}>
            <div className="expect-month">
              <h3>{formatMonth(m.month)}</h3>
              <div className="expect-links">
                <Link className="button button-secondary button-sm" to={`/months/${m.month}`}>
                  {t('expectations.openMonth')}
                </Link>
                <Link className="button button-quiet button-sm" to={`/transactions?month=${m.month}`}>
                  <Icon name="table" size="sm" />
                  {t('expectations.transactions')}
                </Link>
                <Link className="button button-quiet button-sm" to={`/documents?month=${m.month}`}>
                  <Icon name="files" size="sm" />
                  {t('expectations.documents')}
                </Link>
              </div>
            </div>
            <div className="expect-sides">
              {m.moneyIn && <Side label={t('expectations.moneyIn')} side={m.moneyIn} currency={currency} />}
              {m.moneyOut && <Side label={t('expectations.moneyOut')} side={m.moneyOut} currency={currency} />}
            </div>
          </li>
        ))}
      </ul>
    </section>
  )
}
