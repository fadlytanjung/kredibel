/**
 * The words of the loan readiness report (spec 025): percentages, the period and each check's
 * sentence from its id, status and facts (locales/en/readiness.json). Shared by the page and tested.
 */
import type { ReadinessCheck } from '../../entities/readiness'
import { formatMonth } from '../../shared/lib/formatDate'

type T = (key: string, options?: Record<string, unknown>) => string

function months(list: string[]): string {
  return list.map((m) => formatMonth(m)).join(', ')
}

/** "92.2%"; a policy threshold such as 0.85 reads "85%". */
export function percent(rate: string | null | undefined, digits = 1): string {
  if (rate == null) return '—'
  const value = Number(rate) * 100
  return `${digits ? value.toFixed(digits) : Math.round(value)}%`
}

export function periodText(list: string[], t: T): string {
  if (list.length === 0) return ''
  const first = list[0]
  const last = list[list.length - 1]
  if (first === last) return formatMonth(first)
  const sameYear = first.slice(0, 4) === last.slice(0, 4)
  return t('dashboard:periodRange', { first: formatMonth(first, sameYear ? 'long' : 'longYear'), last: formatMonth(last) })
}

/** The words of a check, from its id, status and facts (readiness.json). */
export function checkText(check: ReadinessCheck, t: T): string {
  const key = `checks.${check.id}`
  const facts = { count: check.count ?? 0, months: months(check.months), threshold: check.id === 'RECONCILED' ? percent(check.threshold, 0) : check.threshold }
  if (check.id === 'CASH' && check.status === 'WARN') {
    return (check.count ?? 0) > 0 ? t(`${key}.WARN_days`, facts) : t(`${key}.WARN_net`)
  }
  return t(`${key}.${check.status}`, facts)
}
