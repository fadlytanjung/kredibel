/**
 * DashboardPage (spec 010, T010-04/T010-06; docs/11 §6.2; mock design/mocks/dashboard.html).
 *
 * Every number comes from GET /api/dashboard, computed by code from the workspace's statements:
 * the status sentence, the period's figures against the previous period, the open findings, where
 * the money went in short, and one tab per month. A workspace without data sees the upload empty
 * state (AC-001-3, AC-010-3). "Where the money went" draws the period's money flow, months and
 * cash-flow statement (T010-05).
 */

import { useTranslation } from 'react-i18next'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { type Dashboard, type Framework, useDashboard } from '../entities/insight'
import { useWorkspace } from '../entities/workspace'
import { formatMonth } from '../shared/lib/formatDate'
import { Button } from '../shared/ui/Button'
import { EmptyState } from '../shared/ui/EmptyState'
import { Icon } from '../shared/ui/Icon'
import {
  AlertList,
  ChartsSection,
  currentMonthIn,
  ExpectationsPanel,
  FlowSummary,
  KpiCard,
  MonthStrip,
  type PeriodParts,
  PeriodPicker,
  parsePeriod,
  periodKey,
  ReviewPreview,
  SuggestionCard,
} from '../widgets/dashboard'

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

function Body({ data, name, period, framework, currency, expectations }: { data: Dashboard; name: string; period: string; framework?: Framework; currency?: string; expectations?: boolean }) {
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
      <header className="stack gap-1">
        <h1 className="type-title">{name || t('overview')}</h1>
        <p className="greeting muted">{t('greeting', { name, range })}</p>
      </header>

      <section className="ledger" aria-label={t('figuresAria', { range })}>
        <dl className="ledger-figures">
          {data.kpis.map((kpi) => (
            <KpiCard key={kpi.id} kpi={kpi} />
          ))}
        </dl>
      </section>

      {expectations && <ExpectationsPanel currency={currency ?? 'IDR'} />}

      <ChartsSection period={period} range={range} framework={framework} />

      <section className="status-hero" aria-labelledby="status-h">
        <div className="section-head">
          <h2 className="type-h2" id="status-h">
            {t('reconciliationHealth')}
          </h2>
          <div className="actions">
            {worst && (
              <Link className="button button-secondary button-sm" to={`/months/${worst.month}`}>
                {t('seeMonth', { month: monthName(worst.month, false) })}
              </Link>
            )}
            <Link
              className="button button-quiet button-sm"
              to={`/assistant?q=${encodeURIComponent(`What is the reconciliation status for ${range || 'this period'}?`)}`}
            >
              <Icon name="sparkles" size="sm" />
              {t('askAboutThis')}
            </Link>
          </div>

        </div>
        <p className="status-sentence">
          <span className="done">{t('reconciled', { done, count: inPeriod.length })}</span>{' '}
          <span className="ask">{alerts.length ? t('openFindings', { count: alerts.length }) : t('nothingOpen')}</span>
        </p>
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
      </section>

      <div className="dash-lists">
        <AlertList alerts={alerts} />
        <ReviewPreview items={data.reviewPreview ?? []} />
        <SuggestionCard />
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
  const [params, setParams] = useSearchParams()
  const { data: workspace } = useWorkspace(true)
  // The current month where the workspace keeps its books, unless the address names a period.
  const current = currentMonthIn(workspace?.timezone)
  const parts: PeriodParts = parsePeriod(params.get('period')) ?? { kind: 'month', from: current, to: current }
  const period = periodKey(parts)
  const { data, isLoading, isError } = useDashboard(period)
  const choose = (next: PeriodParts) => {
    const q = new URLSearchParams(params)
    q.set('period', periodKey(next))
    setParams(q, { replace: true })
  }

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

  const withData = data.months.map((m) => m.month).sort()
  const latestWithData = withData[withData.length - 1]
  return (
    <div className="page">
      <div className="dash-period">
        <PeriodPicker value={parts} onChange={choose} dataMonths={withData} current={current} />
      </div>
      {withData.length > 0 && !(data.periodMonths ?? []).some((m) => withData.includes(m)) && (
        <p className="period-empty" role="status">
          {t('dashboard:periods.noBooks', { range: rangeOf(data.periodMonths ?? [], (key, o) => t(`dashboard:${key}`, o)) })}{' '}
          <button type="button" className="link-button" onClick={() => choose({ kind: 'month', from: latestWithData, to: latestWithData })}>
            {t('dashboard:periods.showLatest', { month: formatMonth(latestWithData, 'longYear') })}
          </button>
        </p>
      )}
      <Body data={data} name={workspace?.name ?? ''} period={period} framework={workspace?.profile?.accountingFramework as Framework | undefined} currency={workspace?.currency} expectations={Boolean(workspace?.expectations?.length)} />
    </div>
  )
}
