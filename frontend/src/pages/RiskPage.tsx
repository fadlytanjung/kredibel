/**
 * RiskPage (spec 008, AC-008-7, AC-008-8, AC-008-10).
 *
 * Lists open findings grouped by month, most severe first, with severity filters,
 * month risk levels at the top, and EvidenceViewer dialog/drawer.
 */

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
import { formatMonth } from '../shared/lib/formatDate'
import { DataTable, type DataTableColumn, type DataTableFilter } from '../shared/ui'
import { Icon } from '../shared/ui/Icon'

const SEVERITY_ORDER: SeverityLevel[] = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO']

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

  const { data: monthsData } = useMonths()
  const { data: findingsData, isLoading } = useFindings()

  const months = monthsData?.items ?? []
  const allFindings = [...(findingsData?.items ?? [])].sort(
    (x, y) =>
      SEVERITY_ORDER.indexOf(x.severity) - SEVERITY_ORDER.indexOf(y.severity) ||
      (y.month ?? '').localeCompare(x.month ?? ''),
  )
  const attentionCount = months.filter(
    (m) => m.risk?.level === 'CRITICAL' || m.risk?.level === 'HIGH',
  ).length
  // Previous and next in the evidence viewer follow the list's order.
  const currentIdx = allFindings.findIndex((f) => f.findingId === findingId)

  const filterDefs: { key: string; label: string; predicate: (f: Finding) => boolean }[] = [
    { key: 'ALL', label: t('risk:filters.all'), predicate: () => true },
    { key: 'CRITICAL', label: t('risk:filters.critical'), predicate: (f) => f.severity === 'CRITICAL' },
    { key: 'HIGH', label: t('risk:filters.high'), predicate: (f) => f.severity === 'HIGH' },
    { key: 'MEDIUM', label: t('risk:filters.medium'), predicate: (f) => f.severity === 'MEDIUM' },
    { key: 'LOW', label: t('risk:filters.low'), predicate: (f) => f.severity === 'LOW' },
    { key: 'HELD', label: t('risk:filters.held'), predicate: (f) => f.category === 'DUPLICATE' },
  ]
  const filters: DataTableFilter<Finding>[] = filterDefs.map((f) => ({
    ...f,
    count: allFindings.filter(f.predicate).length,
  }))
  const where = (f: Finding) =>
    f.docId
      ? f.evidence?.[0]?.page
        ? t('risk:table.documentPage', { page: f.evidence[0].page })
        : t('risk:table.document')
      : t('risk:table.wholeMonth')
  const columns: DataTableColumn<Finding>[] = [
    {
      key: 'finding',
      header: t('risk:table.finding'),
      wideOnMobile: true,
      sortable: true,
      sortValue: (f) => SEVERITY_ORDER.indexOf(f.severity),
      render: (f) => (
        <div className="stack gap-1">
          <span className="row gap-2 items-center flex-wrap">
            <SeverityBadge severity={f.severity} />
            <span className="code-tag">{f.code.split('_')[0]}</span>
          </span>
          <strong>{f.title}</strong>
          <span className="reason">{where(f)}</span>
        </div>
      ),
    },
    {
      key: 'month',
      header: t('risk:table.month'),
      sortable: true,
      sortValue: (f) => f.month ?? '',
      render: (f) => (f.month ? formatMonth(f.month) : '\u2014'),
    },
    {
      key: 'status',
      header: t('risk:table.status'),
      align: 'right',
      sortable: true,
      sortValue: (f) => f.status,
      render: (f) => (
        <span
          className={`status-line ${
            f.status === 'OPEN'
              ? f.severity === 'CRITICAL' || f.severity === 'HIGH'
                ? 'bad'
                : ''
              : f.status === 'DISMISSED'
                ? 'good'
                : 'wait'
          }`}
        >
          {t(`risk:status.${f.status.toLowerCase()}`, { defaultValue: f.status })}
        </span>
      ),
    },
  ]

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

        <DataTable
          data={allFindings}
          columns={columns}
          getRowKey={(f) => f.findingId}
          filters={filters}
          filterGroupAriaLabel={t('risk:filterBySeverity')}
          searchable
          searchPlaceholder={t('risk:search')}
          searchPredicate={(f, q) =>
            [f.title, f.code, f.month ?? '', f.month ? formatMonth(f.month) : '', ...(f.nextSteps ?? [])].some((text) =>
              text.toLowerCase().includes(q),
            )
          }
          isLoading={isLoading}
          loadingMessage={<p className="muted small">{t('common:loading')}</p>}
          emptyMessage={<p className="muted small">{t('risk:noFindings')}</p>}
          rowClassName={(f) => (f.severity === 'CRITICAL' || f.severity === 'HIGH' ? 'is-flagged' : '')}
          onRowClick={(f) => navigate(`/risk/${f.findingId}`)}
        />

        {/* Clean months footer note */}
        <p className="muted small">{t('risk:cleanMonths')}</p>
      </div>

      {/* Evidence Viewer Drawer/Dialog */}
      {findingId && (
        <EvidenceViewer
          findingId={findingId}
          onClose={() => navigate('/risk')}
          onNext={
            currentIdx >= 0 && currentIdx < allFindings.length - 1
              ? () => navigate(`/risk/${allFindings[currentIdx + 1].findingId}`)
              : undefined
          }
          onPrev={
            currentIdx > 0
              ? () => navigate(`/risk/${allFindings[currentIdx - 1].findingId}`)
              : undefined
          }
          index={currentIdx >= 0 ? currentIdx : undefined}
          total={allFindings.length}
        />
      )}
    </div>
  )
}
