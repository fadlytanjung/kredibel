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
  /** Digits after the decimal point; defaults to the currency's own (ADR-020), up to two when compact. */
  fractionDigits?: number
}

const DECIMAL = /^-?\d+(\.\d+)?$/

// Rupiah are shown whole, as the mocks do; yen have no minor unit. Ringgit, Singapore and US
// dollars keep their cents (ADR-020).
const WHOLE_UNITS = new Set(['IDR', 'JPY'])

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
    minimumFractionDigits: fractionDigits ?? (compact || WHOLE_UNITS.has(currency) ? 0 : 2),
    maximumFractionDigits: fractionDigits ?? (compact ? 2 : WHOLE_UNITS.has(currency) ? 0 : 2),
  })
  return formatter.format(amount as Intl.StringNumericLiteral)
}

/**
 * The amount alone, with the currency's own minor digits (ADR-020): for places that print the
 * currency once beside it, such as a figure with its code in small type.
 */
export function formatAmount(amount: string, options: Omit<FormatMoneyOptions, 'code' | 'compact'> = {}): string {
  const { currency = 'IDR', fractionDigits } = options
  if (!DECIMAL.test(amount)) {
    return ''
  }
  const digits = fractionDigits ?? (WHOLE_UNITS.has(currency) ? 0 : 2)
  return new Intl.NumberFormat(activeLocale(), {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(amount as Intl.StringNumericLiteral)
}
