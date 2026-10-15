/** The period's open findings, most severe first (spec 010, T010-04, AC-010-1, AC-010-2). */

import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { SeverityBadge, type SeverityLevel } from '../../entities/finding'
import type { Alert } from '../../entities/insight'
import { formatMonth } from '../../shared/lib/formatDate'

export function AlertList({ alerts }: { alerts: Alert[] }) {
  const { t } = useTranslation('dashboard')
  return (
    <section className="panel" aria-labelledby="dash-risk-h">
      <div className="panel-head">
        <h2 id="dash-risk-h">{t('risk')}</h2>
        <Link className="link" to="/risk">
          {t('allFindings')}
        </Link>
      </div>
      {alerts.length === 0 ? (
        <p className="muted small panel-pad">{t('noAlerts')}</p>
      ) : (
        <ul className="alert-list">
          {alerts.map((alert) => (
            <li key={alert.findingId ?? alert.link}>
              <Link to={alert.link}>
                <span className="sev">
                  <SeverityBadge severity={alert.severity as SeverityLevel} />
                </span>
                <span>
                  <p className="a-t">{alert.title}</p>
                  {alert.month && <p className="a-s">{formatMonth(alert.month)}</p>}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
