/**
 * MonthsPage (`/months/all`): one row per month with its state and statements (spec 007, AC-007-12).
 * The navigation opens the current month instead (docs/11 §4.2). The bank evidence, documents-first
 * and currency views come back on the workspace's own data in T007-10c.
 */

import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { useMonths } from '../entities/month'
import { useWorkspace } from '../entities/workspace'
import { formatMonth } from '../shared/lib/formatDate'
import { Badge } from '../shared/ui'

const STATE_BADGE = {
  COLLECTING: 'outline',
  RECONCILING: 'low',
  NEEDS_REVIEW: 'medium',
  RECONCILED: 'clean',
  SIGNED_OFF: 'clean',
} as const

export function MonthsPage() {
  const { t } = useTranslation(['months', 'common'])
  const { data: monthsData, isLoading } = useMonths()
  const { data: ws } = useWorkspace(true)
  const months = [...(monthsData?.items ?? [])].sort((a, b) => b.month.localeCompare(a.month))

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
        {isLoading ? (
          <p className="muted">{t('months:all.loading')}</p>
        ) : months.length === 0 ? (
          <div className="empty-state stack gap-3">
            <p className="muted">{t('months:all.empty')}</p>
            <Link to="/documents?upload=1" className="button button-primary">
              {t('months:all.uploadDocuments')}
            </Link>
          </div>
        ) : (
          <div className="table-panel rt-wrap">
            <table className="data-table rt">
              <thead>
                <tr>
                  <th>{t('months:all.colMonth')}</th>
                  <th>{t('months:all.colStatus')}</th>
                  <th>{t('months:all.colStatements')}</th>
                  <th className="r">{t('months:all.colAction')}</th>
                </tr>
              </thead>
              <tbody>
                {months.map((m) => (
                  <tr key={m.month}>
                    <td>
                      <strong>{formatMonth(m.month)}</strong>
                      {m.note && <div className="reason">{m.note}</div>}
                    </td>
                    <td>
                      <Badge variant={STATE_BADGE[m.state] ?? 'default'}>{t(`months:monthDetail.states.${m.state}`)}</Badge>
                    </td>
                    <td>{t('months:all.statementsCount', { count: m.statements?.length ?? 0 })}</td>
                    <td className="r">
                      <Link to={`/months/${encodeURIComponent(m.month)}`} className="button button-secondary button-sm">
                        {t('months:all.viewDetails')}
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}
