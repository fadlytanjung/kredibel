/**
 * The dashboard's period (spec 010, AC-010-1): one month (the current one by default), a range of at
 * most 12 months, or a year, as the API's period keys ("2026-10", "2026-08..2026-10", "2026").
 */

export type PeriodKind = 'month' | 'range' | 'year'
export const MAX_RANGE_MONTHS = 12
const MONTH = /^\d{4}-(0[1-9]|1[0-2])$/

export const monthIndex = (month: string) => Number(month.slice(0, 4)) * 12 + Number(month.slice(5, 7)) - 1
export const monthAt = (index: number) => `${String(Math.floor(index / 12)).padStart(4, '0')}-${String((index % 12) + 1).padStart(2, '0')}`
export const addMonths = (month: string, n: number) => monthAt(monthIndex(month) + n)

/** Today's month where the workspace keeps its books (its time zone), else in this browser. */
export function currentMonthIn(timeZone?: string | null, now: Date = new Date()): string {
  try {
    const parts = new Intl.DateTimeFormat('en-CA', { timeZone: timeZone || undefined, year: 'numeric', month: '2-digit' }).formatToParts(now)
    const year = parts.find((p) => p.type === 'year')?.value
    const month = parts.find((p) => p.type === 'month')?.value
    if (year && month) return `${year}-${month}`
  } catch {
    // An unknown time zone falls back to the browser's.
  }
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
}

export interface PeriodParts {
  kind: PeriodKind
  from: string // first month of the period
  to: string // last month of the period
}

/** A period key the dashboard offers, or null for anything else (old keys such as "recent"). */
export function parsePeriod(key: string | null | undefined): PeriodParts | null {
  if (!key) return null
  if (/^\d{4}$/.test(key)) return { kind: 'year', from: `${key}-01`, to: `${key}-12` }
  if (MONTH.test(key)) return { kind: 'month', from: key, to: key }
  const [from, to] = key.split('..')
  if (from && to && MONTH.test(from) && MONTH.test(to)) {
    const length = monthIndex(to) - monthIndex(from) + 1
    if (length >= 1 && length <= MAX_RANGE_MONTHS) return { kind: 'range', from, to }
  }
  return null
}

export function periodKey(parts: PeriodParts): string {
  if (parts.kind === 'year') return parts.from.slice(0, 4)
  if (parts.kind === 'month') return parts.from
  return `${parts.from}..${parts.to}`
}

/** The months people can pick, newest first: from the earliest books (or two years back) to today. */
export function monthOptions(dataMonths: string[], current: string): string[] {
  const sorted = [...dataMonths].sort()
  const last = Math.max(monthIndex(current), sorted.length ? monthIndex(sorted[sorted.length - 1]) : 0)
  const first = Math.min(monthIndex(current) - 23, sorted.length ? monthIndex(sorted[0]) : Infinity)
  const out: string[] = []
  for (let i = last; i >= first; i -= 1) out.push(monthAt(i))
  return out
}

export function yearOptions(dataMonths: string[], current: string): string[] {
  const months = monthOptions(dataMonths, current)
  return [...new Set(months.map((m) => m.slice(0, 4)))]
}

/** A range kept inside the rules: `to` not before `from`, at most 12 months, not past `latest`. */
export function clampRange(from: string, to: string, latest: string): PeriodParts {
  let end = monthIndex(to) > monthIndex(latest) ? latest : to
  if (monthIndex(end) < monthIndex(from)) end = from
  if (monthIndex(end) - monthIndex(from) + 1 > MAX_RANGE_MONTHS) end = addMonths(from, MAX_RANGE_MONTHS - 1)
  return { kind: 'range', from, to: end }
}

/** Switching kind keeps the place: a month becomes the three months ending with it, or its year. */
export function switchKind(parts: PeriodParts, kind: PeriodKind, current: string): PeriodParts {
  if (kind === parts.kind) return parts
  const anchor = monthIndex(parts.to) > monthIndex(current) ? current : parts.to
  if (kind === 'month') return { kind, from: anchor, to: anchor }
  if (kind === 'year') return { kind, from: `${anchor.slice(0, 4)}-01`, to: `${anchor.slice(0, 4)}-12` }
  const from = parts.kind === 'year' ? parts.from : addMonths(anchor, -2)
  return clampRange(from, anchor, current)
}
