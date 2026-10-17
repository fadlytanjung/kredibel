/**
 * RunsPage (`/runs`, owner only; spec 017, AC-017-5…7; docs/11 §6.12): every document, month and
 * assistant run in the shared DataTable (chips by kind, failed and corrected, search, pages); a run
 * opens in a drawer with its span waterfall and the inspector for one call.
 */

import { useTranslation } from 'react-i18next'
import { useNavigate, useParams } from 'react-router-dom'
import { type Run, useRun, useRunEvents, useRunsByKind } from '../entities/run'
import { useAuth } from '../entities/session'
import { DataTable, type DataTableColumn, type DataTableFilter, Icon, type IconName } from '../shared/ui'
import { durationMs, kTokens, RunDrawer, runTitle, seconds, shortModel, startedAt } from '../widgets/runs'

const KIND_ICON: Record<string, IconName> = { DOCUMENT: 'files', MONTH: 'reconcile', ASSISTANT: 'sparkles' }
const STATUS_TONE: Record<string, string> = { DONE: 'ok', RUNNING: 'busy', QUEUED: 'wait', SUPERSEDED: 'wait', FAILED: 'bad' }

export function RunsPage() {
  const { me } = useAuth()
  return <RunsContent role={me?.role ?? undefined} known={Boolean(me)} />
}

/** The page for a known role; the preview passes it directly (no sign-in) with its own base path. */
export function RunsContent({ role, known = true, basePath = '/runs' }: { role?: string | null; known?: boolean; basePath?: string }) {
  const { t } = useTranslation(['runs', 'common'])
  const navigate = useNavigate()
  const { runId } = useParams<{ runId?: string }>()
  const owner = role === 'owner'
  const { data, isLoading, isError, refetch } = useRunsByKind(100, owner)
  const { data: run } = useRun(owner ? runId : undefined)
  const { data: events } = useRunEvents(runId, owner)

  if (known && !owner) {
    return (
      <div className="page">
        <div className="page-head">
          <h1 className="type-title">{t('runs:title')}</h1>
          <p>{t('runs:notOwner')}</p>
        </div>
      </div>
    )
  }
  const runs = data?.items ?? []
  const count = (test: (r: Run) => boolean) => runs.filter(test).length
  const tests: { key: string; test: (r: Run) => boolean }[] = [
    { key: 'all', test: () => true },
    { key: 'DOCUMENT', test: (r) => r.kind === 'DOCUMENT' },
    { key: 'MONTH', test: (r) => r.kind === 'MONTH' },
    // Assistant runs come with the assistant's runner (spec 011); the chip stays, counting none.
    { key: 'ASSISTANT', test: (r) => String(r.kind) === 'ASSISTANT' },
    { key: 'failed', test: (r) => r.status === 'FAILED' },
    { key: 'corrected', test: (r) => (r.labels?.corrected ?? 0) > 0 },
  ]
  const filters: DataTableFilter<Run>[] = tests.map(({ key, test }) => ({ key, label: t(`runs:chips.${key}`), predicate: test, count: count(test) }))
  const llmCalls = (r: Run) => r.usage?.llmCalls ?? (r.stages ?? []).filter((s) => s.model).length
  const labelsCell = (r: Run) => {
    const parts = [
      r.labels?.proposed ? t('runs:labelsCell.proposed', { count: r.labels.proposed }) : null,
      r.labels?.verified ? t('runs:labelsCell.verified', { count: r.labels.verified }) : null,
      r.labels?.corrected ? t('runs:labelsCell.corrected', { count: r.labels.corrected }) : null,
    ].filter(Boolean)
    return parts.length ? parts.join(', ') : t('runs:none')
  }
  const columns: DataTableColumn<Run>[] = [
    {
      key: 'run',
      header: t('runs:columns.run'),
      wideOnMobile: true,
      render: (r) => (
        <span className="doc-cell">
          <span className="thumb">
            <Icon name={KIND_ICON[r.kind] ?? 'files'} />
          </span>
          <span>
            <strong>{runTitle(r, t)}</strong>
            <span className="sub">{t('runs:kindRun', { kind: t(`runs:kinds.${r.kind}`) })}</span>
          </span>
        </span>
      ),
    },
    {
      key: 'status',
      header: t('runs:columns.status'),
      render: (r) => <span className={`status-line ${STATUS_TONE[r.status] ?? ''}`}>{t(`runs:status.${r.status}`, { defaultValue: r.status })}</span>,
    },
    { key: 'started', header: t('runs:columns.started'), hideOnMobile: true, sortable: true, sortValue: (r) => r.createdAt ?? '', render: (r) => startedAt(r.createdAt) },
    { key: 'duration', header: t('runs:columns.duration'), align: 'right', render: (r) => (r.endedAt ? seconds(durationMs(r.createdAt, r.endedAt)) : '—') },
    { key: 'calls', header: t('runs:columns.calls'), align: 'right', hideOnMobile: true, render: (r) => llmCalls(r) },
    {
      key: 'tokens',
      header: t('runs:columns.tokens'),
      align: 'right',
      hideOnMobile: true,
      render: (r) => (r.usage?.tokensIn ? `${kTokens(r.usage.tokensIn)} / ${kTokens(r.usage.tokensOut)}` : t('runs:none')),
    },
    { key: 'usd', header: t('runs:columns.usd'), align: 'right', hideOnMobile: true, render: (r) => r.usage?.estimatedUsd ?? '—' },
    { key: 'models', header: t('runs:columns.models'), hideOnMobile: true, className: 'small', render: (r) => (r.models?.length ? r.models.map(shortModel).join(', ') : t('runs:none')) },
    { key: 'labels', header: t('runs:columns.labels'), hideOnMobile: true, className: 'small', render: labelsCell },
  ]

  return (
    <div className="page">
      <div className="page-head">
        <div className="spread">
          <h1 className="type-title">{t('runs:title')}</h1>
          <span className="badge badge-outline">{t('runs:ownerOnly')}</span>
        </div>
        <p>{t('runs:intro')}</p>
      </div>
      {isError ? (
        <p role="alert">
          {t('runs:error')}{' '}
          <button type="button" className="button button-secondary button-sm" onClick={() => void refetch()}>
            {t('runs:retry')}
          </button>
        </p>
      ) : (
        <DataTable
          data={runs}
          columns={columns}
          getRowKey={(r) => r.runId}
          filters={filters}
          filterGroupAriaLabel={t('runs:filter')}
          searchPlaceholder={t('runs:search')}
          searchPredicate={(r, q) => [r.target, r.targetName ?? '', r.runId].some((text) => text.toLowerCase().includes(q))}
          isLoading={isLoading}
          loadingMessage={<p className="muted">{t('runs:loading')}</p>}
          emptyMessage={<p className="muted">{t('runs:empty')}</p>}
          onRowClick={(r) => navigate(`${basePath}/${encodeURIComponent(r.runId)}`)}
          selectedRowKey={runId}
          tableClassName="runs-table"
        />
      )}
      {run && <RunDrawer run={run} events={events?.items ?? []} onClose={() => navigate(basePath)} />}
    </div>
  )
}
