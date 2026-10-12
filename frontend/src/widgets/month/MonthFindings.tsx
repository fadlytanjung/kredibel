/**
 * A month's open findings, most severe first (spec 007, T007-10d): filters by severity with counts,
 * search, 10 a page; a row opens the finding's evidence.
 */

import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { type Finding, SeverityBadge, type SeverityLevel } from '../../entities/finding'
import { DataTable, type DataTableColumn, type DataTableFilter } from '../../shared/ui'

const SEVERITIES: SeverityLevel[] = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']

export function MonthFindings({ findings }: { findings: Finding[] }) {
  const { t } = useTranslation(['months', 'risk'])
  const navigate = useNavigate()
  if (findings.length === 0) return <p className="muted">{t('months:monthDetail.findings.none')}</p>
  const sorted = [...findings].sort((a, b) => SEVERITIES.indexOf(a.severity as SeverityLevel) - SEVERITIES.indexOf(b.severity as SeverityLevel))
  const filters: DataTableFilter<Finding>[] = [
    { key: 'all', label: t('months:monthDetail.docs.filterAll'), predicate: () => true, count: sorted.length },
    ...SEVERITIES.map((level) => ({
      key: level,
      label: t(`risk:severity.${level}`, { defaultValue: level }),
      predicate: (f: Finding) => f.severity === level,
      count: sorted.filter((f) => f.severity === level).length,
    })).filter((f) => f.count > 0),
  ]
  const columns: DataTableColumn<Finding>[] = [
    {
      key: 'severity',
      header: t('months:monthDetail.findings.colSeverity'),
      sortable: true,
      sortValue: (f) => SEVERITIES.indexOf(f.severity as SeverityLevel),
      render: (f) => <SeverityBadge severity={f.severity as SeverityLevel} />,
    },
    {
      key: 'finding',
      header: t('months:monthDetail.findings.colFinding'),
      wideOnMobile: true,
      render: (f) => (
        <div>
          <strong>{f.title}</strong>
          {f.nextSteps?.[0] && <div className="reason">{f.nextSteps[0]}</div>}
        </div>
      ),
    },
  ]
  return (
    <DataTable
      data={sorted}
      columns={columns}
      getRowKey={(f) => f.findingId}
      filters={filters}
      filterGroupAriaLabel={t('months:monthDetail.tabs.findings')}
      searchable
      searchPlaceholder={t('months:monthDetail.findings.search')}
      searchPredicate={(f, q) => [f.title, f.code, ...(f.nextSteps ?? [])].some((text) => text.toLowerCase().includes(q))}
      onRowClick={(f) => navigate(`/risk/${f.findingId}`)}
    />
  )
}
