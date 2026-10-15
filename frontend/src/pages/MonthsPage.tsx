/**
 * MonthsPage (`/months/all`): one row per month with its state and statements (spec 007, AC-007-12).
 * The navigation opens the current month instead (docs/11 §4.2). The bank evidence, documents-first
 * and currency views come back on the workspace's own data in T007-10c.
 */

import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router-dom'
import { SeverityBadge, type SeverityLevel } from '../entities/finding'
import { useMonths } from '../entities/month'
import { useWorkspace } from '../entities/workspace'
import { formatMonth } from '../shared/lib/formatDate'
import { Badge, DataTable, type DataTableColumn, type DataTableFilter } from '../shared/ui'

const STATE_BADGE = {
  COLLECTING: 'outline',
  RECONCILING: 'low',
  NEEDS_REVIEW: 'medium',
  RECONCILED: 'clean',
  SIGNED_OFF: 'clean',
} as const
const RISK_ORDER = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']

type MonthRow = NonNullable<ReturnType<typeof useMonths>['data']>['items'][number]

export function MonthsPage() {
  const { t } = useTranslation(['months', 'common'])
  const navigate = useNavigate()
  const { data: monthsData, isLoading } = useMonths()
  const { data: ws } = useWorkspace(true)
  const months = [...(monthsData?.items ?? [])].sort((a, b) => b.month.localeCompare(a.month))
  const byState = (states: string[]) => (m: MonthRow) => states.includes(m.state)
  const filterDefs = [
    { key: 'all', label: t('months:all.filterAll'), predicate: () => true },
    { key: 'review', label: t('months:monthDetail.states.NEEDS_REVIEW'), predicate: byState(['NEEDS_REVIEW']) },
    { key: 'collecting', label: t('months:monthDetail.states.COLLECTING'), predicate: byState(['COLLECTING', 'RECONCILING']) },
    { key: 'done', label: t('months:monthDetail.states.RECONCILED'), predicate: byState(['RECONCILED', 'SIGNED_OFF']) },
  ]
  const filters: DataTableFilter<MonthRow>[] = filterDefs.map((f) => ({ ...f, count: months.filter(f.predicate).length }))
  const columns: DataTableColumn<MonthRow>[] = [
    {
      key: 'month',
      header: t('months:all.colMonth'),
      wideOnMobile: true,
      sortable: true,
      sortValue: (m) => m.month,
      render: (m) => (
        <div>
          <strong>{formatMonth(m.month)}</strong>
          {m.note && <div className="reason">{m.note}</div>}
        </div>
      ),
    },
    {
      key: 'state',
      header: t('months:all.colStatus'),
      sortable: true,
      sortValue: (m) => m.state,
      render: (m) => (
        <Badge variant={STATE_BADGE[m.state] ?? 'default'}>{t(`months:monthDetail.states.${m.state}`)}</Badge>
      ),
    },
    {
      key: 'risk',
      header: t('months:all.colRisk'),
      sortable: true,
      sortValue: (m) => RISK_ORDER.indexOf(m.risk?.level ?? ''),
      render: (m) => (m.risk?.level ? <SeverityBadge severity={m.risk.level as SeverityLevel} /> : <span className="muted small">{t('months:all.noRisk')}</span>),
    },
    {
      key: 'statements',
      header: t('months:all.colStatements'),
      hideOnMobile: true,
      render: (m) => t('months:all.statementsCount', { count: m.statements?.length ?? 0 }),
    },
  ]

  return (
    <div className="page stack gap-6">
      <header className="stack gap-2">
        <h1 className="type-title">{t('months:title')}</h1>
        <p className="muted">{t('months:subtitle')}</p>
        {ws?.currency && <p className="muted">{t('months:workspaceCurrency', { currency: ws.currency })}</p>}
      </header>

      <section className="stack gap-4" aria-labelledby="all-months-h">
        <h2 className="type-h2" id="all-months-h">
          {t('months:all.title')}
        </h2>
        {!isLoading && months.length === 0 ? (
          <div className="empty-state stack gap-3">
            <p className="muted">{t('months:all.empty')}</p>
            <Link to="/documents?upload=1" className="button button-primary">
              {t('months:all.uploadDocuments')}
            </Link>
          </div>
        ) : (
          <DataTable
            data={months}
            columns={columns}
            getRowKey={(m) => m.month}
            filters={filters}
            filterGroupAriaLabel={t('months:all.filterLabel')}
            searchable
            searchPlaceholder={t('months:all.search')}
            searchPredicate={(m, q) =>
              [m.month, formatMonth(m.month), t(`months:monthDetail.states.${m.state}`), m.note ?? ''].some((text) =>
                text.toLowerCase().includes(q),
              )
            }
            isLoading={isLoading}
            loadingMessage={<p className="muted">{t('months:all.loading')}</p>}
            onRowClick={(m) => navigate(`/months/${m.month}`)}
          />
        )}
      </section>
    </div>
  )
}
