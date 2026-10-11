/**
 * Format money for display.
 *
 * Normative reference: docs/09-data-model.md §2 (money is a decimal string in JSON), AC-001-14.
 */

import { activeLocale } from './activeLocale'

export interface FormatMoneyOptions {
  currency?: string
  compact?: boolean
}

const DECIMAL = /^-?\d+(\.\d+)?$/

/**
 * Intl formats the decimal string itself, so no amount ever passes through a float
 * (a float loses digits above 2^53 and rounds cents).
 */
export function formatMoney(amount: string, options: FormatMoneyOptions = {}): string {
  const { currency = 'IDR', compact = false } = options
  if (!DECIMAL.test(amount)) {
    return ''
  }

  const formatter = new Intl.NumberFormat(activeLocale(), {
    style: 'currency',
    currency,
    notation: compact ? 'compact' : 'standard',
    maximumFractionDigits: compact ? 2 : 0,
  })
  return formatter.format(amount as Intl.StringNumericLiteral)
}
