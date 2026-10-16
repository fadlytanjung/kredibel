/**
 * LabelsPage (`/labels`, spec 016, AC-016-5, AC-016-6; docs/11 §6.11): every decision the AI made
 * that a person can check, lowest confidence first, with the summary sentence, task and status
 * filters, bulk confirmation and the label panel.
 */

import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { type Label, useBulkConfirm, useLabels } from '../entities/label'
import { useWorkspace } from '../entities/workspace'
import { Confidence, compact, LabelPanel, sourceWord, StatusPill, valueWord } from '../features/labels'
import { formatDate, formatMonth } from '../shared/lib/formatDate'
import { Icon, SegmentedControl } from '../shared/ui'

const TASKS = ['all', 'DOC_TYPE', 'PAGE_TYPE', 'CATEGORY', 'COUNTERPARTY_ROLE', 'FIELD_VALUE'] as const
const STATUSES = ['needs', 'proposed', 'verified', 'corrected'] as const
type StatusChip = (typeof STATUSES)[number] | 'all'

function filtersFor(task: string, chip: StatusChip) {
  return {
    task: task === 'all' ? undefined : task,
    needsCheck: chip === 'needs' ? true : chip === 'proposed' ? false : undefined,
    status: chip === 'proposed' ? 'AI_PROPOSED' : chip === 'verified' ? 'VERIFIED' : chip === 'corrected' ? 'CORRECTED' : undefined,
    limit: 50,
  }
}

export function LabelsPage() {
  const { t } = useTranslation(['labels', 'months', 'documents', 'common'])
  const navigate = useNavigate()
  const { labelId } = useParams<{ labelId?: string }>()
  const [params, setParams] = useSearchParams()
  const task = TASKS.includes(params.get('task') as (typeof TASKS)[number]) ? (params.get('task') as string) : 'all'
  const chip = (STATUSES as readonly string[]).includes(params.get('status') ?? '') ? (params.get('status') as StatusChip) : 'all'
  const { data, isLoading, isError, refetch } = useLabels(filtersFor(task, chip))
  const { data: workspace } = useWorkspace(true)
  const bulk = useBulkConfirm()
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [status, setStatus] = useState('')

  const items = data?.items ?? []
  const summary = data?.summary
  const total = summary?.total ?? 0
  const checked = (summary?.verified ?? 0) + (summary?.corrected ?? 0)
  const agreement = summary?.aiAgreementOnChecked
  const byTask = summary?.byTask ?? {}
  const byStatus = summary?.byStatus ?? {}
  const needs = summary?.needsCheck ?? 0
  const open = labelId ? items.find((lb) => lb.labelId === labelId) : undefined
  const framework = (workspace?.profile?.accountingFramework ?? 'IFRS').replace('_', ' ')

  const setFilter = (next: { task?: string; status?: StatusChip }) => {
    const nextTask = next.task ?? task
    const nextChip = next.status ?? chip
    const q: Record<string, string> = {}
    if (nextTask !== 'all') q.task = nextTask
    if (nextChip !== 'all') q.status = nextChip
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
  const chipCount = (key: StatusChip) =>
    key === 'needs' ? needs : key === 'proposed' ? Math.max((byStatus.AI_PROPOSED ?? 0) - needs, 0) : key === 'verified' ? (byStatus.VERIFIED ?? 0) : (byStatus.CORRECTED ?? 0)

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
        <div className="chips" role="group" aria-label={t('labels:statusFilter')}>
          {STATUSES.map((key) => (
            <button key={key} type="button" className="chip" aria-pressed={chip === key} onClick={() => setFilter({ status: chip === key ? 'all' : key })}>
              {t(`labels:statuses.${key}`)} <span className="n">{compact(chipCount(key))}</span>
            </button>
          ))}
        </div>
        <div className="bulk-bar">
          <span>
            <strong>{t('labels:selected', { count: selected.size })}</strong>
          </span>
          <button type="button" className="button button-secondary button-sm" disabled={selected.size === 0 || bulk.isPending} onClick={confirmSelected}>
            <Icon name="check" size="sm" />
            {t('labels:confirmSelected')}
          </button>
          <span className="muted small">{t('labels:bulkHint')}</span>
          {status && (
            <span className="muted small" role="status">
              {status}
            </span>
          )}
        </div>
        {isLoading ? (
          <p className="muted">{t('labels:loading')}</p>
        ) : isError ? (
          <p role="alert">
            {t('labels:error')}{' '}
            <button type="button" className="button button-secondary button-sm" onClick={() => void refetch()}>
              {t('labels:retry')}
            </button>
          </p>
        ) : items.length === 0 ? (
          <p className="muted">{t('labels:empty')}</p>
        ) : (
          <div className="lbl-layout">
            <div className="table-panel rt-wrap">
              <table className="data-table rt lbl-table">
                <thead>
                  <tr>
                    <th className="chk hide-rt">
                      <span className="sr-only">{t('labels:columns.select')}</span>
                    </th>
                    <th>{t('labels:columns.subject')}</th>
                    <th>{t('labels:columns.label')}</th>
                    <th>{t('labels:columns.confidence')}</th>
                    <th>{t('labels:columns.status')}</th>
                    <th className="hide-rt">{t('labels:columns.source')}</th>
                    <th className="hide-rt">{t('labels:columns.extraction')}</th>
                    <th className="hide-rt">{t('labels:columns.run')}</th>
                    <th className="hide-rt">{t('labels:columns.dataset')}</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((label) => {
                    const chips = pageChips(label)
                    const sub = subjectSub(label)
                    const decided = decidedSub(label)
                    return (
                      <tr key={label.labelId} className={`is-clickable${open?.labelId === label.labelId ? ' is-selected' : ''}`} onClick={() => navigate(`/labels/${label.labelId}`)}>
                        <td className="chk hide-rt" onClick={(e) => e.stopPropagation()}>
                          <input
                            type="checkbox"
                            aria-label={t('labels:selectRow', { subject: label.subject.display })}
                            checked={selected.has(label.labelId)}
                            disabled={label.status !== 'AI_PROPOSED'}
                            onChange={(e) => toggle(label.labelId, e.target.checked)}
                          />
                        </td>
                        <td data-cell="wide">
                          <span className="lbl-subj">
                            <strong>{label.subject.display}</strong>
                            {sub && <span className="sub">{sub}</span>}
                            {chips.length > 0 && (
                              <span className="page-chips" aria-label={t('labels:pageChips')}>
                                {chips.map((c) => (
                                  <Link
                                    key={c.labelId}
                                    className={`pchip ${c.ai?.confidence !== null && c.ai?.confidence !== undefined ? (c.ai.confidence < 0.7 ? 'lo' : c.ai.confidence < 0.9 ? 'mid' : 'hi') : 'lo'}`}
                                    to={`/labels/${c.labelId}`}
                                    title={t('labels:pageChip', { type: valueWord(t, 'PAGE_TYPE', c.final.value), confidence: (c.ai?.confidence ?? 0).toFixed(2) })}
                                    onClick={(e) => e.stopPropagation()}
                                  >
                                    {t('labels:pageChipText', { page: c.subject.pageNo, type: valueWord(t, 'PAGE_TYPE', c.final.value) })} <b>{(c.ai?.confidence ?? 0).toFixed(2)}</b>
                                  </Link>
                                ))}
                              </span>
                            )}
                          </span>
                        </td>
                        <td data-cell="wide">
                          <span className="task">{t(`labels:tasks.${label.task}`)}</span>
                          <span className="lbl-val">{valueWord(t, label.task, label.final.value)}</span>
                          {decided && <span className="sub">{decided}</span>}
                        </td>
                        <td>
                          <Confidence value={label.ai?.confidence} />
                        </td>
                        <td>
                          <StatusPill label={label} />
                        </td>
                        <td className="hide-rt small muted">{sourceWord(t, label)}</td>
                        <td className="hide-rt">
                          {label.extractionUrl ? (
                            <Link
                              className="md-link"
                              to={`/labels/${label.labelId}`}
                              title={t('labels:openExtraction', { page: label.subject.pageNo ?? 1 })}
                              onClick={(e) => e.stopPropagation()}
                            >
                              <Icon name="markdown" size="sm" />
                              {t('labels:extractionFile', { page: label.subject.pageNo ?? 1 })}
                            </Link>
                          ) : (
                            <span className="muted">{t('labels:noExtraction')}</span>
                          )}
                        </td>
                        <td className="hide-rt">
                          {label.ai?.runId ? (
                            <Link className="run-link" to={`/runs/${encodeURIComponent(label.ai.runId)}`} onClick={(e) => e.stopPropagation()}>
                              {t('labels:runShort', { id: label.ai.runId.slice(-4) })}
                            </Link>
                          ) : (
                            <span className="muted">—</span>
                          )}
                        </td>
                        <td className="hide-rt">
                          <span className={`ds ${label.dataset.use.toLowerCase()}`}>{t(`labels:dataset.${label.dataset.use}`)}</span>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
            {open && <LabelPanel key={open.labelId} label={open} onClose={() => navigate('/labels')} />}
          </div>
        )}
        <div className="spread lbl-foot">
          <p className="muted small">{t('labels:foot', { shown: compact(items.length), total: compact(total) })}</p>
          <button type="button" className="button button-secondary button-sm" disabled>
            <Icon name="download" size="sm" />
            {t('labels:exportLater')}
          </button>
        </div>
      </div>
    </div>
  )
}

