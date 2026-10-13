/**
 * DashboardPage (spec 010, T010-04/T010-06; docs/11 §6.2; mock design/mocks/dashboard.html).
 *
 * Every number comes from GET /api/dashboard, computed by code from the workspace's statements:
 * the status sentence, the period's figures against the previous period, the open findings, where
 * the money went in short, and one tab per month. A workspace without data sees the upload empty
 * state (AC-001-3, AC-010-3). The charts of "Where the money went" arrive with T010-05.
 */

import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router-dom'
import { type Dashboard, useDashboard } from '../entities/insight'
import { useWorkspace } from '../entities/workspace'
import { formatMonth } from '../shared/lib/formatDate'
import { Button } from '../shared/ui/Button'
import { EmptyState } from '../shared/ui/EmptyState'
import { Icon } from '../shared/ui/Icon'
import { AlertList, FlowSummary, KpiCard, MonthStrip, ReviewPreview } from '../widgets/dashboard'

const RISK_ORDER = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']

function monthName(month: string, withYear = true): string {
  return formatMonth(month, withYear ? 'longYear' : 'long')
}

function rangeOf(months: string[], t: (key: string, o?: Record<string, unknown>) => string): string {
  if (months.length === 0) return ''
  const first = months[0]
  const last = months[months.length - 1]
  if (first === last) return monthName(first)
  const sameYear = first.slice(0, 4) === last.slice(0, 4)
  return t('periodRange', { first: monthName(first, !sameYear), last: monthName(last) })
}

function Body({ data, name }: { data: Dashboard; name: string }) {
  const { t } = useTranslation('dashboard')
  const months = data.periodMonths ?? []
  const range = rangeOf(months, t)
  const inPeriod = data.months.filter((m) => months.includes(m.month))
  const done = inPeriod.filter((m) => m.state === 'RECONCILED' || m.state === 'SIGNED_OFF').length
  const alerts = data.alerts ?? []
  const why = alerts.filter((a) => a.severity === 'CRITICAL' || a.severity === 'HIGH').slice(0, 2)
  const worst = [...inPeriod]
    .filter((m) => m.riskLevel)
    .sort((a, b) => RISK_ORDER.indexOf(a.riskLevel ?? 'LOW') - RISK_ORDER.indexOf(b.riskLevel ?? 'LOW'))[0]
  return (
    <div className="dash">
      <section className="status-hero" aria-labelledby="status-h">
        <p className="greeting">{t('greeting', { name, range })}</p>
        <h1 className="status-sentence" id="status-h">
          <span className="done">{t('reconciled', { done, count: inPeriod.length })}</span>{' '}
          <span className="ask">{alerts.length ? t('openFindings', { count: alerts.length }) : t('nothingOpen')}</span>
        </h1>
        {why.length > 0 && (
          <ul className="why">
            {why.map((a) => (
              <li key={a.findingId ?? a.link}>
                <span className={a.severity === 'CRITICAL' ? 'sev-critical' : 'sev-high'}>
                  <Icon name={a.severity === 'CRITICAL' ? 'octagon-alert' : 'triangle-alert'} />
                </span>
                <span>
                  {a.month && <strong>{monthName(a.month, false)}: </strong>}
                  {a.title}
                </span>
              </li>
            ))}
          </ul>
        )}
        <div className="actions">
          {worst && (
            <Link className="button button-secondary button-lg" to={`/months/${worst.month}`}>
              {t('seeMonth', { month: monthName(worst.month, false) })}
            </Link>
          )}
        </div>
      </section>

      <section className="ledger" aria-label={t('figuresAria', { range })}>
        <dl className="ledger-figures">
          {data.kpis.map((kpi) => (
            <KpiCard key={kpi.id} kpi={kpi} />
          ))}
        </dl>
      </section>

      <div className="dash-lists">
        <AlertList alerts={alerts} />
        <ReviewPreview items={data.reviewPreview ?? []} />
        <FlowSummary
          sources={data.moneyFlowSummary?.topSources ?? []}
          uses={data.moneyFlowSummary?.topUses ?? []}
        />
      </div>

      <section aria-labelledby="months-h">
        <div className="section-head">
          <h2 className="type-h2" id="months-h">
            {t('monthsTitle')}
          </h2>
          <Link className="link" to="/months">
            {t('reconciliation')}
          </Link>
        </div>
        <MonthStrip months={data.months} />
      </section>
    </div>
  )
}

export function DashboardPage() {
  const { t } = useTranslation(['dashboard', 'common'])
  const navigate = useNavigate()
  const latestYear = String(new Date().getUTCFullYear())
  const [period, setPeriod] = useState('recent')
  const { data, isLoading, isError } = useDashboard(period)
  const { data: workspace } = useWorkspace(true)
  const periods = [
    { key: 'recent', label: t('dashboard:periods.recent') },
    { key: latestYear, label: t('dashboard:periods.year', { year: latestYear }) },
    { key: 'all', label: t('dashboard:periods.all') },
  ]

  if (isLoading) {
    return (
      <div className="page">
        <p className="muted">{t('dashboard:loading')}</p>
      </div>
    )
  }

  if (isError || !data || data.months.length === 0) {
    return (
      <div className="page">
        <EmptyState
          icon={<Icon name="upload" size="lg" />}
          title={t('common:dashboard.emptyTitle')}
          description={t('common:dashboard.emptyDescription')}
          action={
            <Button size="lg" onClick={() => navigate('/documents?upload=1')}>
              <Icon name="upload" size="sm" />
              {t('common:dashboard.uploadButton')}
            </Button>
          }
        />
      </div>
    )
  }

  return (
    <div className="page">
      <div className="row justify-end mb-4">
        <div className="seg" role="group" aria-label={t('dashboard:periods.label')}>
          {periods.map((p) => (
            <button key={p.key} type="button" aria-pressed={period === p.key} onClick={() => setPeriod(p.key)}>
              {p.label}
            </button>
          ))}
        </div>
      </div>
      <Body data={data} name={workspace?.name ?? ''} />
    </div>
  )
}
