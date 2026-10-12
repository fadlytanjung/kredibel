/**
 * RiskPage (spec 008, AC-008-7, AC-008-8, AC-008-10).
 *
 * Lists open findings grouped by month, most severe first, with severity filters,
 * month risk levels at the top, and EvidenceViewer dialog/drawer.
 */

import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate, useParams } from 'react-router-dom'
import {
  EvidenceViewer,
  SeverityBadge,
  useFindings,
  type Finding,
  type SeverityLevel,
} from '../entities/finding'
import { useMonths } from '../entities/month'
import { Icon } from '../shared/ui/Icon'

type SeverityFilter = 'ALL' | 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'HELD'

function formatMonthTitle(monthStr: string) {
  const [year, mNum] = monthStr.split('-')
  const d = new Date(Date.UTC(Number(year), Number(mNum) - 1, 1))
  const monthName = d.toLocaleDateString('en-US', { month: 'long', timeZone: 'UTC' })
  return `${monthName} ${year}`
}

function parseMonthParts(monthStr: string) {
  const [year, mNum] = monthStr.split('-')
  const d = new Date(Date.UTC(Number(year), Number(mNum) - 1, 1))
  const shortName = d.toLocaleDateString('en-US', { month: 'short', timeZone: 'UTC' })
  return { year, shortName }
}

const MTAB_CLASSES: Record<SeverityLevel, string> = {
  CRITICAL: 'mtab is-critical',
  HIGH: 'mtab is-high',
  MEDIUM: 'mtab is-open',
  LOW: 'mtab',
  INFO: 'mtab',
}

function getMtabClass(level: SeverityLevel): string {
  return MTAB_CLASSES[level] || 'mtab'
}

export function RiskPage() {
  const { t } = useTranslation(['risk', 'common'])
  const navigate = useNavigate()
  const { findingId } = useParams<{ findingId?: string }>()

  const [filter, setFilter] = useState<SeverityFilter>('ALL')

  const { data: monthsData } = useMonths()
  const { data: findingsData, isLoading } = useFindings()

  const months = monthsData?.items ?? []
  const allFindings = findingsData?.items ?? []

  // Filter findings
  const filteredFindings = allFindings.filter((f) => {
    if (filter === 'ALL') return true
    if (filter === 'HELD') return f.category === 'DUPLICATE'
    return f.severity === filter
  })

  // Group findings by month
  const monthOrder = Array.from(
    new Set([
      ...allFindings.map((f) => f.month).filter(Boolean),
      ...months.map((m) => m.month),
    ]),
  ).sort().reverse() as string[]

  const groupsByMonth = monthOrder
    .map((mStr) => {
      const monthFindings = filteredFindings.filter((f) => f.month === mStr)
      const monthObj = months.find((m) => m.month === mStr)
      const level = (monthObj?.risk?.level ?? 'LOW') as SeverityLevel
      return {
        month: mStr,
        monthObj,
        level,
        findings: monthFindings,
      }
    })
    .filter((g) => g.findings.length > 0 || (filter === 'ALL' && g.level !== 'LOW'))

  // Count months needing attention (CRITICAL or HIGH)
  const attentionCount = months.filter(
    (m) => m.risk?.level === 'CRITICAL' || m.risk?.level === 'HIGH',
  ).length

  // Counts for filter chips
  const countAll = allFindings.length
  const countCritical = allFindings.filter((f) => f.severity === 'CRITICAL').length
  const countHigh = allFindings.filter((f) => f.severity === 'HIGH').length
  const countMedium = allFindings.filter((f) => f.severity === 'MEDIUM').length
  const countLow = allFindings.filter((f) => f.severity === 'LOW').length
  const countHeld = allFindings.filter((f) => f.category === 'DUPLICATE').length

  // Finding index inside filtered list for prev/next
  const currentIdx = filteredFindings.findIndex((f) => f.findingId === findingId)

  return (
    <div className="page stack gap-6">
      {/* Page Header */}
      <div className="page-head">
        <h1 className="type-title">{t('risk:title')}</h1>
        <p>
          <strong>
            {t(
              attentionCount === 1 ? 'risk:attention_one' : 'risk:attention_other',
              { count: attentionCount },
            )}
          </strong>{' '}
          {t('risk:subtitle')}
        </p>
      </div>

      <div className="stack gap-6">
        {/* Risk by month top horizontal tabs */}
        {months.length > 0 && (
          <section aria-label={t('risk:riskByMonth')}>
            <div className="months-wrap">
              <ol className="months">
                {months.map((m) => {
                  const { year, shortName } = parseMonthParts(m.month)
                  const level = (m.risk?.level ?? 'LOW') as SeverityLevel
                  const mtabClass = getMtabClass(level)
                  return (
                    <li key={m.month}>
                      <Link className={mtabClass} to={`/months/${m.month}`}>
                        <span className="m-name">
                          <strong>{shortName}</strong>
                          <span>{year}</span>
                        </span>
                        <span className="m-state wait">
                          <Icon name="inbox" size="sm" />
                          {m.risk?.reasons?.[0] ?? m.state}
                        </span>
                        <span className="m-foot">
                          <SeverityBadge severity={level} />
                        </span>
                      </Link>
                    </li>
                  )
                })}
              </ol>
            </div>
          </section>
        )}

        {/* Severity Filter Chips */}
        <div className="chips" role="group" aria-label={t('risk:filterBySeverity')}>
          <button
            type="button"
            className={`chip ${filter === 'ALL' ? 'is-active' : ''}`}
            aria-pressed={filter === 'ALL'}
            onClick={() => setFilter('ALL')}
          >
            {t('risk:filters.all')} <span className="n">{countAll}</span>
          </button>
          <button
            type="button"
            className={`chip ${filter === 'CRITICAL' ? 'is-active' : ''}`}
            aria-pressed={filter === 'CRITICAL'}
            onClick={() => setFilter('CRITICAL')}
          >
            {t('risk:filters.critical')} <span className="n">{countCritical}</span>
          </button>
          <button
            type="button"
            className={`chip ${filter === 'HIGH' ? 'is-active' : ''}`}
            aria-pressed={filter === 'HIGH'}
            onClick={() => setFilter('HIGH')}
          >
            {t('risk:filters.high')} <span className="n">{countHigh}</span>
          </button>
          <button
            type="button"
            className={`chip ${filter === 'MEDIUM' ? 'is-active' : ''}`}
            aria-pressed={filter === 'MEDIUM'}
            onClick={() => setFilter('MEDIUM')}
          >
            {t('risk:filters.medium')} <span className="n">{countMedium}</span>
          </button>
          <button
            type="button"
            className={`chip ${filter === 'LOW' ? 'is-active' : ''}`}
            aria-pressed={filter === 'LOW'}
            onClick={() => setFilter('LOW')}
          >
            {t('risk:filters.low')} <span className="n">{countLow}</span>
          </button>
          <button
            type="button"
            className={`chip ${filter === 'HELD' ? 'is-active' : ''}`}
            aria-pressed={filter === 'HELD'}
            onClick={() => setFilter('HELD')}
          >
            {t('risk:filters.held')} <span className="n">{countHeld}</span>
          </button>
        </div>

        {/* Loading / Empty / Findings list */}
        {isLoading ? (
          <p className="muted small">{t('common:loading')}</p>
        ) : groupsByMonth.length === 0 ? (
          <p className="muted small">{t('risk:noFindings')}</p>
        ) : (
          groupsByMonth.map((group) => {
            if (group.findings.length === 0) return null
            const title = formatMonthTitle(group.month)
            return (
              <section
                key={group.month}
                className="find-group"
                aria-label={title}
              >
                <div className="find-head">
                  <h2 className="type-h3">{title}</h2>
                  <SeverityBadge severity={group.level} />
                  <Link className="link" to={`/months/${group.month}`}>
                    {t('risk:openMonth', { month: group.month })}
                  </Link>
                </div>

                <div className="table-panel rt-wrap">
                  <table className="data-table rt find-table">
                    <thead>
                      <tr>
                        <th>{t('risk:table.finding')}</th>
                        <th className="hide-rt">{t('risk:table.where')}</th>
                        <th className="r">{t('risk:table.status')}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {group.findings.map((f: Finding) => {
                        const where = f.docId
                          ? `${f.docId}${f.evidence?.[0]?.page ? `, page ${f.evidence[0].page}` : ''}`
                          : group.month
                        const shortCode = f.code.split('_')[0]
                        const isFlagged =
                          f.severity === 'CRITICAL' || f.severity === 'HIGH'

                        return (
                          <tr
                            key={f.findingId}
                            className={isFlagged ? 'is-flagged' : undefined}
                          >
                            <td>
                              <button
                                type="button"
                                className="find-link text-left"
                                onClick={() => navigate(`/risk/${f.findingId}`)}
                              >
                                <SeverityBadge severity={f.severity} />
                                <span className="code-tag">{shortCode}</span>
                                <span className="find-t">{f.title}</span>
                              </button>
                              <span className="sub">{where}</span>
                            </td>
                            <td className="hide-rt">{where}</td>
                            <td className="r">
                              <span
                                className={`status-line ${
                                  f.status === 'OPEN'
                                    ? isFlagged
                                      ? 'bad'
                                      : ''
                                    : f.status === 'DISMISSED'
                                      ? 'good'
                                      : 'wait'
                                }`}
                              >
                                {f.status}
                              </span>
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              </section>
            )
          })
        )}

        {/* Clean months footer note */}
        <p className="muted small">{t('risk:cleanMonths')}</p>
      </div>

      {/* Evidence Viewer Drawer/Dialog */}
      {findingId && (
        <EvidenceViewer
          findingId={findingId}
          onClose={() => navigate('/risk')}
          onNext={
            currentIdx >= 0 && currentIdx < filteredFindings.length - 1
              ? () => navigate(`/risk/${filteredFindings[currentIdx + 1].findingId}`)
              : undefined
          }
          onPrev={
            currentIdx > 0
              ? () => navigate(`/risk/${filteredFindings[currentIdx - 1].findingId}`)
              : undefined
          }
          index={currentIdx >= 0 ? currentIdx : undefined}
          total={filteredFindings.length}
        />
      )}
    </div>
  )
}
