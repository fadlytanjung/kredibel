/** Numbers and times the way the Runs page prints them (and the mock, from the same rules). */

import type { Run } from '../../entities/run'

export const kTokens = (n: number | null | undefined) => (n ? `${(n / 1000).toFixed(1)}k` : '0')

export const seconds = (ms: number) => `${(ms / 1000).toFixed(1)} s`

export function durationMs(startedAt?: string | null, endedAt?: string | null, now = Date.now()): number {
  if (!startedAt) return 0
  const start = Date.parse(startedAt)
  const end = endedAt ? Date.parse(endedAt) : now
  return Math.max(0, end - start)
}

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

/** "2 Jul, 09:14" in UTC, so the mock and the page agree wherever the check runs. */
export function startedAt(iso: string | null | undefined): string {
  if (!iso) return '—'
  const d = new Date(iso)
  const hh = String(d.getUTCHours()).padStart(2, '0')
  const mm = String(d.getUTCMinutes()).padStart(2, '0')
  return `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]}, ${hh}:${mm}`
}

export function shortModel(model: string | null | undefined): string {
  if (!model) return ''
  const id = model.toLowerCase()
  if (id.includes('flash-lite')) return 'Flash-Lite'
  if (id.includes('flash')) return 'Flash'
  if (id.includes('pro')) return 'Pro'
  return model
}

/** A prompt reference as people read it: "classify_document@2" → "classify_document v2". */
export const promptLabel = (ref: string | null | undefined) => (ref ? ref.replace('@', ' v') : '')

/** Tick steps in seconds: about five ticks whatever the run's length. */
const STEPS = [1, 2, 5, 10, 15, 30, 60, 120, 300, 600, 1800, 3600]

export function tickStep(totalMs: number): number {
  const total = totalMs / 1000
  return STEPS.find((step) => total / step <= 5) ?? STEPS[STEPS.length - 1]
}

/** A run as people name it: the document's file name, or the month with its generation. */
export function runTitle(run: Run, t: (key: string, opts?: Record<string, unknown>) => string): string {
  if (run.kind === 'MONTH' && run.generation) return t('runs:monthTarget', { month: run.target, generation: run.generation })
  return run.targetName ?? run.target
}
