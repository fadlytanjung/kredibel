/**
 * RunsPage (`/runs`, owner only; spec 017, AC-017-5…7; docs/11 §6.12): every document, month and
 * assistant run with its status, duration, calls, tokens, cost, models and labels; the selected
 * run's span waterfall and the inspector for one call.
 */

import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { useAuth } from '../entities/session'
import { type Run, useRun, useRunEvents, useRuns } from '../entities/run'
import { Icon, type IconName } from '../shared/ui'
import { durationMs, kTokens, RunInspector, seconds, shortModel, spanRows, startedAt, Waterfall } from '../widgets/runs'

const CHIPS = ['all', 'DOCUMENT', 'MONTH', 'ASSISTANT', 'failed', 'corrected'] as const
type Chip = (typeof CHIPS)[number]
const KIND_ICON: Record<string, IconName> = { DOCUMENT: 'files', MONTH: 'reconcile', ASSISTANT: 'sparkles' }
const STATUS_TONE: Record<string, string> = { DONE: 'ok', RUNNING: 'busy', QUEUED: 'wait', SUPERSEDED: 'wait', FAILED: 'bad' }

function matches(run: Run, chip: Chip): boolean {
  if (chip === 'all') return true
  if (chip === 'failed') return run.status === 'FAILED'
  if (chip === 'corrected') return (run.labels?.corrected ?? 0) > 0
  return run.kind === chip
}

export function RunsPage() {
  const { me } = useAuth()
  return <RunsContent role={me?.role ?? undefined} known={Boolean(me)} />
}

/** The page for a known role; the preview passes it directly (no sign-in). */
export function RunsContent({ role, known = true }: { role?: string | null; known?: boolean }) {
  const { t } = useTranslation(['runs', 'common'])
  const navigate = useNavigate()
  const { runId } = useParams<{ runId?: string }>()
  const [params, setParams] = useSearchParams()
  const chip: Chip = (CHIPS as readonly string[]).includes(params.get('filter') ?? '') ? (params.get('filter') as Chip) : 'all'
  const owner = role === 'owner'
  const { data, isLoading, isError, refetch } = useRuns({ limit: 100 }, owner)
  const { data: run } = useRun(owner ? runId : undefined)
  const { data: events } = useRunEvents(runId, owner)
  const [selectedKey, setSelectedKey] = useState<string | null>(null)

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
  const runs = (data?.items ?? []).filter((r) => matches(r, chip))
  const counts = (key: Chip) => (data?.items ?? []).filter((r) => matches(r, key)).length
  const llmCalls = (r: Run) => (r.stages ?? []).filter((s) => s.model).length
  const labelsCell = (r: Run) => {
    const parts = [
      r.labels?.proposed ? t('runs:labelsCell.proposed', { count: r.labels.proposed }) : null,
      r.labels?.verified ? t('runs:labelsCell.verified', { count: r.labels.verified }) : null,
      r.labels?.corrected ? t('runs:labelsCell.corrected', { count: r.labels.corrected }) : null,
    ].filter(Boolean)
    return parts.length ? parts.join(', ') : t('runs:none')
  }
  const rows = run ? spanRows(run, t) : []
  const chosen = rows.find((r) => r.key === selectedKey) ?? rows.find((r) => r.kind === 'llm') ?? rows[0]

  return (
    <div className="page">
      <div className="page-head">
        <div className="spread">
          <h1 className="type-title">{t('runs:title')}</h1>
          <span className="badge badge-outline">{t('runs:ownerOnly')}</span>
        </div>
        <p>{t('runs:intro')}</p>
      </div>
      <div className="stack gap-5">
        <div className="chips" role="group" aria-label={t('runs:filter')}>
          {CHIPS.map((key) => (
            <button key={key} type="button" className="chip" aria-pressed={chip === key} onClick={() => setParams(key === 'all' ? {} : { filter: key }, { replace: true })}>
              {t(`runs:chips.${key}`)} <span className="n">{counts(key)}</span>
            </button>
          ))}
        </div>
        {isLoading ? (
          <p className="muted">{t('runs:loading')}</p>
        ) : isError ? (
          <p role="alert">
            {t('runs:error')}{' '}
            <button type="button" className="button button-secondary button-sm" onClick={() => void refetch()}>
              {t('runs:retry')}
            </button>
          </p>
        ) : runs.length === 0 ? (
          <p className="muted">{t('runs:empty')}</p>
        ) : (
          <div className="table-panel rt-wrap">
            <table className="data-table rt runs-table">
              <thead>
                <tr>
                  <th>{t('runs:columns.run')}</th>
                  <th>{t('runs:columns.status')}</th>
                  <th className="hide-rt">{t('runs:columns.started')}</th>
                  <th className="r">{t('runs:columns.duration')}</th>
                  <th className="r hide-rt">{t('runs:columns.calls')}</th>
                  <th className="r hide-rt">{t('runs:columns.tokens')}</th>
                  <th className="r hide-rt">{t('runs:columns.usd')}</th>
                  <th className="hide-rt">{t('runs:columns.models')}</th>
                  <th className="hide-rt">{t('runs:columns.labels')}</th>
                </tr>
              </thead>
              <tbody>
                {runs.map((r) => (
                  <tr key={r.runId} className={`is-clickable${r.runId === runId ? ' is-selected' : ''}`} onClick={() => navigate(`/runs/${encodeURIComponent(r.runId)}`)}>
                    <td data-cell="wide">
                      <span className="doc-cell">
                        <span className="thumb">
                          <Icon name={KIND_ICON[r.kind] ?? 'files'} />
                        </span>
                        <span>
                          <strong>{r.target}</strong>
                          <span className="sub">{t('runs:kindRun', { kind: t(`runs:kinds.${r.kind}`) })}</span>
                        </span>
                      </span>
                    </td>
                    <td>
                      <span className={`status-line ${STATUS_TONE[r.status] ?? ''}`}>{t(`runs:status.${r.status}`, { defaultValue: r.status })}</span>
                    </td>
                    <td className="hide-rt">{startedAt(r.createdAt)}</td>
                    <td className="r">{r.endedAt ? seconds(durationMs(r.createdAt, r.endedAt)) : '—'}</td>
                    <td className="r hide-rt">{llmCalls(r)}</td>
                    <td className="r hide-rt">{r.usage?.tokensIn ? `${kTokens(r.usage.tokensIn)} / ${kTokens(r.usage.tokensOut)}` : t('runs:none')}</td>
                    <td className="r hide-rt">{r.usage?.estimatedUsd ?? '0.000'}</td>
                    <td className="hide-rt small">{r.models?.length ? r.models.map(shortModel).join(', ') : t('runs:none')}</td>
                    <td className="hide-rt small">{labelsCell(r)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {run && (
          <section className="run-detail" aria-labelledby="rd-h">
            <div className="spread">
              <div>
                <h2 className="type-h2" id="rd-h">
                  {t('runs:detail.title', { workflow: t(`runs:detail.workflow.${run.kind}`), target: run.target })}
                </h2>
                <p className="muted small">
                  {t('runs:detail.summary', {
                    started: startedAt(run.createdAt),
                    duration: seconds(durationMs(run.createdAt, run.endedAt)),
                    calls: llmCalls(run),
                    tokensIn: kTokens(run.usage?.tokensIn),
                    tokensOut: kTokens(run.usage?.tokensOut),
                    usd: run.usage?.estimatedUsd ?? '0.000',
                    prompts: Object.values(run.promptVersions ?? {}).join(', ') || t('runs:detail.noPrompts'),
                  })}
                </p>
              </div>
            </div>
            <div className="run-layout">
              <Waterfall run={run} selected={chosen?.key ?? null} onSelect={setSelectedKey} />
              {chosen && <RunInspector run={run} row={chosen} events={events?.items ?? []} />}
            </div>
          </section>
        )}
      </div>
    </div>
  )
}
