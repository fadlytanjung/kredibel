/**
 * One tab per month (spec 010, T010-04, AC-010-9): state, the share matched by Kredibel,
 * statements present of expected, and the risk level; it scrolls on phones and opens the month.
 */

import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { SeverityBadge, type SeverityLevel } from '../../entities/finding'
import type { MonthSummary } from '../../entities/insight'
import { formatMonth } from '../../shared/lib/formatDate'
import { Icon } from '../../shared/ui'

const TINT: Record<string, string> = { CRITICAL: ' is-critical', HIGH: ' is-high', MEDIUM: ' is-open' }
const shortName = (month: string) => formatMonth(month, 'short')

export function MonthStrip({ months }: { months: MonthSummary[] }) {
  const { t } = useTranslation('dashboard')
  return (
    <div className="months-wrap">
      <ol className="months">
        {months.map((m) => {
          const name = shortName(m.month)
          const done = m.state === 'RECONCILED' || m.state === 'SIGNED_OFF'
          const rate = m.autoMatchRate === undefined ? undefined : Math.round(Number(m.autoMatchRate) * 100)
          return (
            <li key={m.month}>
              <Link className={`mtab${TINT[m.riskLevel ?? ''] ?? ''}`} to={`/months/${m.month}`}>
                <span className="m-name">
                  <strong>{name}</strong>
                  <span>{m.month.slice(0, 4)}</span>
                </span>
                <span className={`m-state ${done ? 'ok' : 'wait'}`}>
                  <Icon name={done ? 'check-circle' : 'inbox'} />
                  {t(`states.${m.state}`)}
                </span>
                <span className="m-matched">
                  {rate !== undefined && (
                    <>
                      <span>
                        <b>{rate}%</b> {t('matchedShare')}
                      </span>
                      <span className="meter-bar">
                        <i style={{ width: `${rate}%` }} /* allow-raw-style: the month's automatic match rate */ />
                      </span>
                    </>
                  )}
                  <span>
                    {t('statements', { present: m.statementsPresent ?? 0, expected: m.statementsExpected ?? 0 })}
                  </span>
                </span>
                <span className="m-foot">
                  {m.riskLevel ? (
                    <SeverityBadge severity={m.riskLevel as SeverityLevel} />
                  ) : (
                    <span>{t('noRisk')}</span>
                  )}
                </span>
              </Link>
            </li>
          )
        })}
      </ol>
    </div>
  )
}
