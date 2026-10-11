/**
 * Format monetary amounts according to currency and locale conventions.
 *
 * Normative reference: docs/09-data-model.md §2 and docs/11 §3.
 */

export interface FormatMoneyOptions {
  currency?: string
  compact?: boolean
}

export function formatMoney(
  amount: number | string,
  options: FormatMoneyOptions = {},
): string {
  const { currency = 'IDR', compact = false } = options
  const numericAmount = typeof amount === 'string' ? parseFloat(amount) : amount

  if (isNaN(numericAmount)) {
    return '0'
  }

  const formatter = new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    notation: compact ? 'compact' : 'standard',
    maximumFractionDigits: compact ? 2 : 0,
  })

  return formatter.format(numericAmount)
}
