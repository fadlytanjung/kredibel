/** The rows of a run's waterfall, from its stages (spec 017, AC-017-6). */

import type { Run, RunStage } from '../../entities/run'
import { durationMs, kTokens, shortModel } from './format'

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

export function spanRows(run: Run, t: (key: string, opts?: Record<string, unknown>) => string): SpanRow[] {
  const t0 = run.createdAt ? Date.parse(run.createdAt) : 0
  const total = durationMs(run.createdAt, run.endedAt)
  const stages = run.stages ?? []
  const parents = new Set(stages.map((s) => s.parent).filter(Boolean))
  const rows: SpanRow[] = [
    {
      key: 'root',
      name: t('runs:detail.root', { workflow: t(`runs:detail.workflow.${run.kind}`) }),
      depth: 0,
      kind: 'wf',
      start: 0,
      end: total,
      detail: run.target,
    },
  ]
  const ordered = [...stages].sort((a, b) => Date.parse(a.startedAt ?? '') - Date.parse(b.startedAt ?? ''))
  ordered.forEach((stage, index) => {
    const start = stage.startedAt ? Date.parse(stage.startedAt) - t0 : 0
    const end = stage.endedAt ? Date.parse(stage.endedAt) - t0 : start
    const kind: SpanRow['kind'] = stage.model ? 'llm' : parents.has(stage.node) ? 'node' : 'code'
    const detail = [stage.model ? `${shortModel(stage.model)}, ${kTokens(stage.tokensIn)} in, ${kTokens(stage.tokensOut)} out` : null, stage.summary ?? null]
      .filter(Boolean)
      .join(': ')
    rows.push({ key: `${index}:${stage.node}`, name: `node:${stage.node}`, depth: stage.parent ? 2 : 1, kind, start, end, detail, stage })
  })
  return rows
}
