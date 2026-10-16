/** The rows of a run's waterfall, from its stages (spec 017, AC-017-6). */

import type { Run, RunStage } from '../../entities/run'
import { kTokens, promptLabel, shortModel } from './format'

export interface SpanRow {
  key: string
  name: string
  depth: 0 | 1 | 2
  kind: 'wf' | 'node' | 'llm' | 'code'
  start: number
  end: number
  detail: string
  stage?: RunStage
}

/**
 * The time axis runs from the first stage's start to the last stage's end: a run queued for a
 * while, or one whose end was not recorded, still draws its steps across the whole width.
 */
export function spanRows(run: Run, t: (key: string, opts?: Record<string, unknown>) => string): SpanRow[] {
  const stages = [...(run.stages ?? [])].sort(
    (a, b) => Date.parse(a.startedAt ?? '') - Date.parse(b.startedAt ?? ''),
  )
  const starts = stages.map((s) => Date.parse(s.startedAt ?? '')).filter((n) => !Number.isNaN(n))
  const ends = stages.map((s) => Date.parse(s.endedAt ?? s.startedAt ?? '')).filter((n) => !Number.isNaN(n))
  const t0 = starts.length ? Math.min(...starts) : Date.parse(run.createdAt ?? '') || 0
  const tEnd = ends.length ? Math.max(...ends) : t0
  const parents = new Set(stages.map((s) => s.parent).filter(Boolean))
  const rows: SpanRow[] = [
    {
      key: 'root',
      name: t('runs:detail.root', { workflow: t(`runs:detail.workflow.${run.kind}`) }),
      depth: 0,
      kind: 'wf',
      start: 0,
      end: Math.max(tEnd - t0, 0),
      detail: run.targetName ?? run.target,
    },
  ]
  stages.forEach((stage, index) => {
    const start = stage.startedAt ? Date.parse(stage.startedAt) - t0 : 0
    const end = stage.endedAt ? Date.parse(stage.endedAt) - t0 : start
    const kind: SpanRow['kind'] = stage.model ? 'llm' : parents.has(stage.node) ? 'node' : 'code'
    const call = stage.model
      ? `${shortModel(stage.model)}${stage.promptVersion ? ` ${promptLabel(stage.promptVersion)}` : ''}, ${kTokens(stage.tokensIn)} in, ${kTokens(stage.tokensOut)} out`
      : null
    const detail = [call, stage.summary ?? null].filter(Boolean).join(': ')
    rows.push({ key: `${index}:${stage.node}`, name: `node:${stage.node}`, depth: stage.parent ? 2 : 1, kind, start, end, detail, stage })
  })
  return rows
}
