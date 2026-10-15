/** Numbers and times the way the Runs page prints them (and the mock, from the same rules). */

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

/** The prompt file a node runs with, for the run's promptVersions map. */
export const PROMPT_OF: Record<string, string> = {
  classify_document: 'classify',
  read_page: 'read_page',
  categorize_bank_lines: 'categorize',
  propose_ledger_mapping: 'map_ledger_columns',
  explain_month: 'explain',
  assistant: 'assistant',
}
