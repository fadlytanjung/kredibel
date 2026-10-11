/**
 * Format money for display.
 *
 * Normative reference: docs/09-data-model.md §2 (money is a decimal string in JSON), AC-001-14.
 */

import { activeLocale } from './activeLocale'

export interface FormatMoneyOptions {
  currency?: string
  compact?: boolean
  /** "USD 1.84" (the mocks' style for small amounts) instead of the locale's symbol. */
  code?: boolean
  /** Digits after the decimal point; defaults to none (whole rupiah) or two when compact. */
  fractionDigits?: number
}

const DECIMAL = /^-?\d+(\.\d+)?$/

/**
 * Intl formats the decimal string itself, so no amount ever passes through a float
 * (a float loses digits above 2^53 and rounds cents).
 */
export function formatMoney(amount: string, options: FormatMoneyOptions = {}): string {
  const { currency = 'IDR', compact = false, code = false, fractionDigits } = options
  if (!DECIMAL.test(amount)) {
    return ''
  }

  const formatter = new Intl.NumberFormat(activeLocale(), {
    style: 'currency',
    currency,
    notation: compact ? 'compact' : 'standard',
    currencyDisplay: code ? 'code' : 'symbol',
    minimumFractionDigits: fractionDigits ?? 0,
    maximumFractionDigits: fractionDigits ?? (compact ? 2 : 0),
  })
  return formatter.format(amount as Intl.StringNumericLiteral)
}
