/**
 * One run in a drawer over the Runs list (spec 017, AC-017-6; the kit's drawer, as the evidence
 * viewer): the run's head and summary, its waterfall beside the inspector of the selected call.
 * Esc or the area beside the drawer closes it.
 */

import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import type { AgentEvent, Run } from '../../entities/run'
import { Icon } from '../../shared/ui'
import { durationMs, kTokens, promptLabel, runTitle, seconds, startedAt } from './format'
import { RunInspector } from './RunInspector'
import { spanRows } from './spans'
import { Waterfall } from './Waterfall'

export function RunDrawer({ run, events, onClose }: { run: Run; events: AgentEvent[]; onClose: () => void }) {
  const { t } = useTranslation(['runs', 'common'])
  const close = useRef<HTMLButtonElement>(null)
  const rows = spanRows(run, t)
  const [selectedKey, setSelectedKey] = useState<string | null>(null)
  const chosen = rows.find((r) => r.key === selectedKey) ?? rows.find((r) => r.kind === 'llm') ?? rows[0]

  useEffect(() => {
    close.current?.focus()
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  const usage = run.usage ?? {}
  const prompts = Object.entries(run.promptVersions ?? {}).map(([prompt, version]) => promptLabel(`${prompt}@${version}`))
  return (
    <div className="drawer-frame">
      <div className="drawer-behind" aria-hidden="true" onClick={onClose} />
      <div className="drawer" role="dialog" aria-modal="true" aria-labelledby="rd-h">
        <div className="drawer-head">
          <div className="stack gap-2 flex-1 min-w-0">
            <span className="muted small">{t('runs:detail.kindLine', { kind: t(`runs:kinds.${run.kind}`), started: startedAt(run.createdAt) })}</span>
            <h1 id="rd-h">{t('runs:detail.title', { workflow: t(`runs:detail.workflow.${run.kind}`), target: runTitle(run, t) })}</h1>
            <p className="muted small">
              {t('runs:detail.summary', {
                started: startedAt(run.createdAt),
                duration: seconds(run.endedAt ? durationMs(run.createdAt, run.endedAt) : rows[0]?.end ?? 0),
                calls: usage.llmCalls ?? 0,
                tokensIn: kTokens(usage.tokensIn),
                tokensOut: kTokens(usage.tokensOut),
                usd: usage.estimatedUsd ?? '—',
                prompts: prompts.join(', ') || t('runs:detail.noPrompts'),
              })}
            </p>
          </div>
          <button ref={close} type="button" className="icon-button" aria-label={t('runs:detail.close')} onClick={onClose}>
            <Icon name="x" />
          </button>
        </div>
        <div className="drawer-body">
          {rows.length > 1 ? (
            <>
              <Waterfall rows={rows} selected={chosen?.key ?? null} onSelect={setSelectedKey} />
              {chosen && <RunInspector run={run} row={chosen} events={events} />}
            </>
          ) : (
            <p className="muted p-6">{t('runs:detail.noStages')}</p>
          )}
        </div>
      </div>
    </div>
  )
}
