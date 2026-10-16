/**
 * LabelsPage (`/labels`, spec 016, AC-016-5, AC-016-6; docs/11 §6.11): every decision the AI made
 * that a person can check, lowest confidence first, in the shared DataTable (status chips, search,
 * pages) under the task switch; selected labels confirm in bulk; a label opens in a drawer. Books
 * read before labels existed get theirs from "Create labels from your books".
 */

import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { type Label, useBulkConfirm, useLabel, useLabels, useSyncLabels } from '../entities/label'
import { useAuth } from '../entities/session'
import { useWorkspace } from '../entities/workspace'
import { Confidence, compact, LabelDrawer, sourceWord, StatusPill, valueWord } from '../features/labels'
import { formatDate, formatMonth } from '../shared/lib/formatDate'
import { DataTable, type DataTableColumn, type DataTableFilter, Icon, SegmentedControl } from '../shared/ui'

const TASKS = ['all', 'DOC_TYPE', 'PAGE_TYPE', 'CATEGORY', 'COUNTERPARTY_ROLE', 'FIELD_VALUE'] as const
const STATUSES = ['all', 'needs', 'proposed', 'verified', 'corrected'] as const
type StatusChip = (typeof STATUSES)[number]
const CAN_DECIDE = ['owner', 'accountant', 'reviewer']

function filtersFor(task: string, chip: StatusChip) {
  return {
    task: task === 'all' ? undefined : task,
    needsCheck: chip === 'needs' ? true : chip === 'proposed' ? false : undefined,
    status: chip === 'needs' || chip === 'proposed' ? 'AI_PROPOSED' : chip === 'verified' ? 'VERIFIED' : chip === 'corrected' ? 'CORRECTED' : undefined,
    limit: 200,
  }
}

export function LabelsPage() {
  const { me } = useAuth()
  return <LabelsContent canDecide={CAN_DECIDE.includes(me?.role ?? '')} />
}

/** The page for a known role; the preview passes it directly (no sign-in) with its own base path. */
export function LabelsContent({ canDecide, basePath = '/labels' }: { canDecide: boolean; basePath?: string }) {
  const { t } = useTranslation(['labels', 'months', 'documents', 'common'])
  const navigate = useNavigate()
  const { labelId } = useParams<{ labelId?: string }>()
  const [params, setParams] = useSearchParams()
  const task = TASKS.includes(params.get('task') as (typeof TASKS)[number]) ? (params.get('task') as string) : 'all'
  const chip = (STATUSES as readonly string[]).includes(params.get('status') ?? '') ? (params.get('status') as StatusChip) : 'all'
  const { data, isLoading, isError, refetch } = useLabels(filtersFor(task, chip))
  const { data: workspace } = useWorkspace(true)
  const bulk = useBulkConfirm()
  const sync = useSyncLabels()
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [status, setStatus] = useState('')

  const items = data?.items ?? []
  const listed = labelId ? items.find((lb) => lb.labelId === labelId) : undefined
  // A label linked from elsewhere (a run's inspector) may not be on this page of the list.
  const { data: fetched } = useLabel(labelId && !listed && !isLoading ? labelId : undefined)
  const open = listed ?? fetched
  const summary = data?.summary
  const total = summary?.total ?? 0
  const checked = (summary?.verified ?? 0) + (summary?.corrected ?? 0)
  const agreement = summary?.aiAgreementOnChecked
  const byTask = summary?.byTask ?? {}
  const byStatus = summary?.byStatus ?? {}
  const needs = summary?.needsCheck ?? 0
  const framework = (workspace?.profile?.accountingFramework ?? 'IFRS').replace('_', ' ')

  const setFilter = (next: { task?: string; status?: StatusChip }) => {
    const nextTask = next.task ?? task
    const nextChip = next.status ?? chip
    const q: Record<string, string> = {}
    if (nextTask !== 'all') q.task = nextTask
    if (nextChip !== 'all') q.status = nextChip
    setSelected(new Set())
    setParams(q, { replace: true })
  }
  const pageChips = (label: Label) =>
    label.subject.docId
      ? items
          .filter((lb) => lb.task === 'PAGE_TYPE' && lb.subject.docId === label.subject.docId && lb.subject.pageNo)
          .sort((a, b) => (a.subject.pageNo ?? 0) - (b.subject.pageNo ?? 0))
      : []
  const subjectSub = (label: Label) =>
    [label.month ? formatMonth(label.month, 'long') : null, label.subject.pageNo ? `p${label.subject.pageNo}` : null, label.subject.field ?? null]
      .filter(Boolean)
      .join(' · ')
  const decidedSub = (label: Label) =>
    label.status === 'AI_PROPOSED'
      ? ''
      : [
          t('labels:decided', { by: label.decidedBy ?? '', when: label.decidedAt ? formatDate(label.decidedAt.slice(0, 10)) : '' }),
          label.status === 'CORRECTED' && label.ai ? t('labels:was', { value: valueWord(t, label.task, label.ai.value) }) : null,
        ]
          .filter(Boolean)
          .join('. ')
  const toggle = (id: string, on: boolean) =>
    setSelected((prev) => {
      const next = new Set(prev)
      if (on) next.add(id)
      else next.delete(id)
      return next
    })
  const confirmSelected = () =>
    bulk.mutate([...selected], {
      onSuccess: (res) => {
        setStatus(t('labels:bulkDone', { count: res.updated }))
        setSelected(new Set())
      },
    })
  const createFromBooks = () =>
    sync.mutate(undefined, {
      onSuccess: (res) => setStatus(res.created ? t('labels:syncDone', { count: res.created, shown: compact(res.created) }) : t('labels:syncNone')),
    })
  const chipCount = (key: StatusChip) =>
    key === 'all'
      ? total
      : key === 'needs'
        ? needs
        : key === 'proposed'
          ? Math.max((byStatus.AI_PROPOSED ?? 0) - needs, 0)
          : key === 'verified'
            ? (byStatus.VERIFIED ?? 0)
            : (byStatus.CORRECTED ?? 0)
  // The server filters by status; the chips only choose, with the workspace's counts.
  const filters: DataTableFilter<Label>[] = STATUSES.map((key) => ({ key, label: t(`labels:statuses.${key}`), count: chipCount(key) }))
  const confidenceTone = (c: Label) => {
    const value = c.ai?.confidence
    if (value === null || value === undefined) return 'lo'
    return value < 0.7 ? 'lo' : value < 0.9 ? 'mid' : 'hi'
  }

  const columns: DataTableColumn<Label>[] = [
    {
      key: 'select',
      header: <span className="sr-only">{t('labels:columns.select')}</span>,
      hideOnMobile: true,
      className: 'chk',
      render: (label) => (
        <input
          type="checkbox"
          aria-label={t('labels:selectRow', { subject: label.subject.display })}
          checked={selected.has(label.labelId)}
          disabled={!canDecide || label.status !== 'AI_PROPOSED'}
          onClick={(e) => e.stopPropagation()}
          onKeyDown={(e) => e.stopPropagation()}
          onChange={(e) => toggle(label.labelId, e.target.checked)}
        />
      ),
    },
    {
      key: 'subject',
      header: t('labels:columns.subject'),
      wideOnMobile: true,
      render: (label) => {
        const chips = pageChips(label)
        const sub = subjectSub(label)
        return (
          <span className="lbl-subj">
            <strong>{label.subject.display}</strong>
            {sub && <span className="sub">{sub}</span>}
            {chips.length > 0 && (
              <span className="page-chips" aria-label={t('labels:pageChips')}>
                {chips.map((c) => (
                  <Link
                    key={c.labelId}
                    className={`pchip ${confidenceTone(c)}`}
                    to={`${basePath}/${c.labelId}`}
                    title={t('labels:pageChip', { type: valueWord(t, 'PAGE_TYPE', c.final.value), confidence: (c.ai?.confidence ?? 0).toFixed(2) })}
                    onClick={(e) => e.stopPropagation()}
                  >
                    {t('labels:pageChipText', { page: c.subject.pageNo, type: valueWord(t, 'PAGE_TYPE', c.final.value) })} <b>{(c.ai?.confidence ?? 0).toFixed(2)}</b>
                  </Link>
                ))}
              </span>
            )}
          </span>
        )
      },
    },
    {
      key: 'label',
      header: t('labels:columns.label'),
      wideOnMobile: true,
      render: (label) => {
        const decided = decidedSub(label)
        return (
          <>
            <span className="task">{t(`labels:tasks.${label.task}`)}</span>
            <span className="lbl-val">{valueWord(t, label.task, label.final.value)}</span>
            {decided && <span className="sub">{decided}</span>}
          </>
        )
      },
    },
    { key: 'confidence', header: t('labels:columns.confidence'), render: (label) => <Confidence value={label.ai?.confidence} /> },
    { key: 'status', header: t('labels:columns.status'), render: (label) => <StatusPill label={label} /> },
    { key: 'source', header: t('labels:columns.source'), hideOnMobile: true, className: 'small muted', render: (label) => sourceWord(t, label) },
    {
      key: 'extraction',
      header: t('labels:columns.extraction'),
      hideOnMobile: true,
      render: (label) =>
        label.extractionUrl ? (
          <Link
            className="md-link"
            to={`${basePath}/${label.labelId}`}
            title={t('labels:openExtraction', { page: label.subject.pageNo ?? 1 })}
            onClick={(e) => e.stopPropagation()}
          >
            <Icon name="markdown" size="sm" />
            {t('labels:extractionFile', { page: label.subject.pageNo ?? 1 })}
          </Link>
        ) : (
          <span className="muted">{t('labels:noExtraction')}</span>
        ),
    },
    {
      key: 'run',
      header: t('labels:columns.run'),
      hideOnMobile: true,
      render: (label) =>
        label.ai?.runId ? (
          <Link className="run-link" to={`/runs/${encodeURIComponent(label.ai.runId)}`} onClick={(e) => e.stopPropagation()}>
            {t('labels:runShort', { id: label.ai.runId.slice(-4) })}
          </Link>
        ) : (
          <span className="muted">—</span>
        ),
    },
    {
      key: 'dataset',
      header: t('labels:columns.dataset'),
      hideOnMobile: true,
      render: (label) => <span className={`ds ${label.dataset.use.toLowerCase()}`}>{t(`labels:dataset.${label.dataset.use}`)}</span>,
    },
  ]
  const syncButton = (
    <button type="button" className="button button-secondary button-sm" disabled={sync.isPending} onClick={createFromBooks}>
      <Icon name="sparkles" size="sm" />
      {t(sync.isPending ? 'labels:syncing' : 'labels:sync')}
    </button>
  )

  return (
    <div className="page">
      <div className="page-head">
        <h1 className="type-title">{t('labels:title')}</h1>
        <p>
          <strong>
            {checked > 0 && agreement !== null && agreement !== undefined
              ? t('labels:lead', { checked: compact(checked), total: compact(total), agreement: `${(agreement * 100).toFixed(1)}%` })
              : t('labels:leadNoneChecked')}{' '}
            {t('labels:needCheck', { count: needs })}
          </strong>{' '}
          {t('labels:intro')}
        </p>
      </div>
      <div className="stack gap-3">
        <div className="spread lbl-tools">
          <SegmentedControl
            ariaLabel={t('labels:taskLabel')}
            value={task}
            onChange={(key) => setFilter({ task: key })}
            options={TASKS.map((key) => ({ key, label: `${t(`labels:tasks.${key}`)} ${compact(key === 'all' ? total : (byTask[key] ?? 0))}` }))}
          />
          <span className="fw-pill">
            <Icon name="book" size="sm" />
            {t('labels:framework', { framework })} <Link to="/settings/profile">{t('labels:changeFramework')}</Link>
          </span>
        </div>
        {isError ? (
          <p role="alert">
            {t('labels:error')}{' '}
            <button type="button" className="button button-secondary button-sm" onClick={() => void refetch()}>
              {t('labels:retry')}
            </button>
          </p>
        ) : (
          <DataTable
            data={items}
            columns={columns}
            getRowKey={(label) => label.labelId}
            filters={filters}
            activeFilter={chip}
            onFilterChange={(key) => setFilter({ status: key as StatusChip })}
            filterGroupAriaLabel={t('labels:statusFilter')}
            searchPlaceholder={t('labels:search')}
            searchPredicate={(label, q) =>
              [label.subject.display, label.subject.field ?? '', valueWord(t, label.task, label.final.value), t(`labels:tasks.${label.task}`)].some((text) =>
                text.toLowerCase().includes(q),
              )
            }
            headerActions={
              canDecide ? (
                <>
                  <span className="muted small">{t('labels:selected', { count: selected.size })}</span>
                  <button type="button" className="button button-secondary button-sm" disabled={selected.size === 0 || bulk.isPending} onClick={confirmSelected}>
                    <Icon name="check" size="sm" />
                    {t('labels:confirmSelected')}
                  </button>
                  {syncButton}
                </>
              ) : undefined
            }
            isLoading={isLoading}
            loadingMessage={<p className="muted">{t('labels:loading')}</p>}
            emptyMessage={
              <div className="stack items-center gap-3">
                <p>{t('labels:empty')}</p>
                {canDecide && total === 0 && (
                  <>
                    <p className="small">{t('labels:emptyCanSync')}</p>
                    {syncButton}
                  </>
                )}
              </div>
            }
            footer={
              <div className="spread lbl-foot">
                <p className="muted small">{t('labels:foot', { shown: compact(items.length), total: compact(total) })}</p>
                <button type="button" className="button button-secondary button-sm" disabled>
                  <Icon name="download" size="sm" />
                  {t('labels:exportLater')}
                </button>
              </div>
            }
            onRowClick={(label) => navigate({ pathname: `${basePath}/${label.labelId}`, search: params.toString() })}
            selectedRowKey={open?.labelId}
            tableClassName="lbl-table"
          />
        )}
        {status && (
          <p className="muted small" role="status">
            {status}
          </p>
        )}
      </div>
      {open && <LabelDrawer key={open.labelId} label={open} onClose={() => navigate({ pathname: basePath, search: params.toString() })} />}
    </div>
  )
}
