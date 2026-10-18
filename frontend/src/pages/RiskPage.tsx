/**
 * RiskPage (spec 008, AC-008-7, AC-008-8, AC-008-10; parity with design/mocks/risk.html, spec 019).
 *
 * The dashboard's month strip, severity chips, then one group per month (the worst month first)
 * listing its findings: badge, code, title, where it was found and its status. A held copy reads
 * "Held". Every finding opens the evidence viewer; months without findings are named at the foot.
 */

import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useQueries } from '@tanstack/react-query'
import { type Document, useDocuments } from '../entities/document'
import { apiClient } from '../shared/api/client'
import {
  EvidenceViewer,
  SeverityBadge,
  useFindings,
  type Finding,
  type SeverityLevel,
} from '../entities/finding'
import { useDashboard } from '../entities/insight'
import { formatMonth } from '../shared/lib/formatDate'
import { MonthStrip } from '../widgets/dashboard'

const RANK: Record<string, number> = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3, INFO: 4 }
const SHOWN = new Set(['OPEN', 'ACKNOWLEDGED']) // dismissed and resolved stay in the audit trail
const CHIPS = ['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'HELD'] as const
type Chip = (typeof CHIPS)[number]

const matches = (f: Finding, chip: Chip) =>
  chip === 'ALL' ? true : chip === 'HELD' ? f.category === 'DUPLICATE' : f.severity === chip

/** 'A', 'A and B', 'A, B and C' (English UI). */
const andList = (items: string[]) =>
  items.length <= 1 ? (items[0] ?? '') : `${items.slice(0, -1).join(', ')} and ${items[items.length - 1]}`

export function RiskPage() {
  const { t } = useTranslation(['risk', 'common'])
  const navigate = useNavigate()
  const { findingId } = useParams<{ findingId?: string }>()
  const [chip, setChip] = useState<Chip>('ALL')

  const { data: dashboard } = useDashboard('all')
  const { data: findingsData, isLoading } = useFindings()
  const { data: documents } = useDocuments({ limit: 200 })

  const months = dashboard?.months ?? []
  const shown = (findingsData?.items ?? []).filter((f) => SHOWN.has(f.status))
  // A busy workspace has more documents than one page; any a finding names is fetched by its ID.
  const listed = new Map((documents?.items ?? []).map((d) => [d.docId, d.fileName]))
  const named = [...new Set(shown.flatMap((f) => [f.docId, ...f.evidence.map((e) => e.docId)]))].filter(
    (id): id is string => Boolean(id) && Boolean(documents) && !listed.has(id as string),
  )
  const fetched = useQueries({
    queries: named.map((docId) => ({
      queryKey: ['document', docId],
      queryFn: () => apiClient<Document>(`/api/documents/${docId}`),
    })),
  })
  const files = new Map([...listed, ...fetched.flatMap((q) => (q.data ? [[q.data.docId, q.data.fileName] as const] : []))])
  const levels = new Map(months.map((m) => [m.month, m.riskLevel]))

  const byMonth = new Map<string, Finding[]>()
  for (const f of shown) {
    const month = f.month ?? ''
    byMonth.set(month, [...(byMonth.get(month) ?? []), f])
  }
  const groupLevel = (month: string): SeverityLevel =>
    (levels.get(month) as SeverityLevel | undefined) ??
    [...(byMonth.get(month) ?? [])].sort((a, b) => RANK[a.severity] - RANK[b.severity])[0].severity
  const groups = [...byMonth.keys()]
    .sort((a, b) => RANK[groupLevel(a)] - RANK[groupLevel(b)] || a.localeCompare(b))
    .map((month) => ({
      month,
      level: groupLevel(month),
      rows: (byMonth.get(month) ?? [])
        .filter((f) => matches(f, chip))
        .sort(
          (a, b) =>
            RANK[a.severity] - RANK[b.severity] ||
            a.code.localeCompare(b.code) ||
            a.findingId.localeCompare(b.findingId),
        ),
    }))
    .filter((g) => g.rows.length > 0)
  const ordered = groups.flatMap((g) => g.rows)
  const currentIdx = ordered.findIndex((f) => f.findingId === findingId)

  const attention = months.filter((m) => m.riskLevel === 'CRITICAL' || m.riskLevel === 'HIGH')
  const lead =
    attention.length === 0
      ? t('risk:attentionNone')
      : t('risk:attention', {
          count: attention.length,
          list: andList(
            attention.map((m) =>
              t('risk:monthIs', {
                month: formatMonth(m.month, 'long'),
                level: t(`risk:severity.${m.riskLevel}`).toLowerCase(),
              }),
            ),
          ),
        })
  const clean = months.filter((m) => !byMonth.has(m.month)).map((m) => formatMonth(m.month, 'long'))

  const where = (f: Finding) => {
    const docId = f.docId ?? f.evidence.find((e) => e.docId)?.docId
    if (!docId) return t('risk:table.wholeMonth')
    const file = files.get(docId) ?? docId
    if (f.scope === 'MONTH') return t('risk:table.monthDocument', { month: formatMonth(f.month ?? '', 'long'), file })
    const page = f.evidence.find((e) => e.docId === docId && e.page)?.page
    return page ? t('risk:table.documentPage', { file, page }) : t('risk:table.document', { file })
  }
  const status = (f: Finding): { label: string; tone: string } => {
    if (f.category === 'DUPLICATE' && f.status === 'OPEN') return { label: t('risk:status.held'), tone: 'wait' }
    const label = t(`risk:status.${f.status.toLowerCase()}`, { defaultValue: f.status })
    if (f.status !== 'OPEN') return { label, tone: '' }
    const tone = f.severity === 'CRITICAL' || f.severity === 'HIGH' ? 'bad' : f.severity === 'MEDIUM' ? 'wait' : ''
    return { label, tone }
  }

  return (
    <div className="page stack gap-6">
      <div className="page-head">
        <h1 className="type-title">{t('risk:title')}</h1>
        <p>
          <strong>{lead}</strong> {t('risk:subtitle')}
        </p>
      </div>

      <div className="stack gap-6">
        {months.length > 0 && (
          <section aria-label={t('risk:riskByMonth')}>
            <MonthStrip months={months} />
          </section>
        )}

        <div className="chips" role="group" aria-label={t('risk:filterBySeverity')}>
          {CHIPS.map((key) => (
            <button
              key={key}
              type="button"
              className="chip"
              aria-pressed={chip === key}
              onClick={() => setChip(key)}
            >
              {t(`risk:filters.${key.toLowerCase()}`)} <span className="n">{shown.filter((f) => matches(f, key)).length}</span>
            </button>
          ))}
        </div>

        {isLoading ? (
          <p className="muted small">{t('common:loading')}</p>
        ) : shown.length === 0 ? (
          <p className="muted small">{t('risk:noOpenFindings')}</p>
        ) : groups.length === 0 ? (
          <p className="muted small">{t('risk:noFindings')}</p>
        ) : (
          groups.map((g) => {
            const heading = formatMonth(g.month)
            return (
              <section key={g.month} className="find-group" aria-label={heading}>
                <div className="find-head">
                  <h2 className="type-h3">{heading}</h2>
                  <SeverityBadge severity={g.level} />
                  <Link className="link" to={`/months/${g.month}`}>
                    {t('risk:openMonth', { month: formatMonth(g.month, 'long') })}
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
                      {g.rows.map((f) => {
                        const place = where(f)
                        const st = status(f)
                        return (
                          <tr key={f.findingId} className={f.severity === 'CRITICAL' ? 'is-flagged' : undefined}>
                            <td>
                              <Link className="find-link" to={`/risk/${f.findingId}`}>
                                <SeverityBadge severity={f.severity} />
                                <span className="code-tag">{f.code.split('_')[0]}</span>
                                <span className="find-t">{f.title}</span>
                              </Link>
                              <span className="sub">{place}</span>
                            </td>
                            <td className="hide-rt">{place}</td>
                            <td className="r">
                              <span className={`status-line ${st.tone}`.trim()}>{st.label}</span>
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

        {clean.length > 0 && shown.length > 0 && (
          <p className="muted small">{t('risk:cleanMonths', { count: clean.length, months: andList(clean) })}</p>
        )}
      </div>

      {findingId && (
        <EvidenceViewer
          findingId={findingId}
          onClose={() => navigate('/risk')}
          onNext={
            currentIdx >= 0 && currentIdx < ordered.length - 1
              ? () => navigate(`/risk/${ordered[currentIdx + 1].findingId}`)
              : undefined
          }
          onPrev={currentIdx > 0 ? () => navigate(`/risk/${ordered[currentIdx - 1].findingId}`) : undefined}
          index={currentIdx >= 0 ? currentIdx : undefined}
          total={ordered.length}
        />
      )}
    </div>
  )
}
