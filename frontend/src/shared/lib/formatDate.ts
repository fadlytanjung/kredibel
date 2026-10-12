/**
 * Format dates for display.
 *
 * Normative reference: docs/13 §4 (calendar dates have no zone; instants are UTC), AC-001-14.
 */

import { activeLocale } from './activeLocale'

const CALENDAR_DATE = /^(\d{4})-(\d{2})-(\d{2})$/

function toDate(input: string | Date | number): Date {
  if (typeof input === 'string') {
    // new Date('2026-10-11') is UTC midnight, which is 10 Oct west of UTC. A calendar date is
    // the same day everywhere, so build it in local time.
    const match = CALENDAR_DATE.exec(input)
    if (match) {
      return new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]))
    }
  }
  return input instanceof Date ? input : new Date(input)
}

export function formatDate(
  dateInput: string | Date | number,
  options?: Intl.DateTimeFormatOptions,
): string {
  if (dateInput === '' || dateInput === null || dateInput === undefined) {
    return ''
  }

  const date = toDate(dateInput)
  if (Number.isNaN(date.getTime())) {
    return ''
  }

  return new Intl.DateTimeFormat(activeLocale(), {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    ...options,
  }).format(date)
}

const MONTH_STYLE: Record<'short' | 'long' | 'longYear', Intl.DateTimeFormatOptions> = {
  short: { month: 'short' },
  long: { month: 'long' },
  longYear: { month: 'long', year: 'numeric' },
}

/** A calendar month (2026-03) in the active locale: "Mar", "March" or "March 2026". */
export function formatMonth(month: string, style: 'short' | 'long' | 'longYear' = 'longYear'): string {
  const [year, number] = month.split('-').map(Number)
  if (!year || !number) return month
  return new Intl.DateTimeFormat(activeLocale(), MONTH_STYLE[style]).format(new Date(year, number - 1, 1))
}
