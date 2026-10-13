/**
 * Chart amounts in millions or thousands, as the mock prints them ("412.5", IDR millions). The
 * decimal point moves in the string, so no amount becomes a float; only geometry uses numbers.
 */

import { formatAmount } from '../../shared/lib/formatMoney'

export type UnitKey = 'millions' | 'thousands' | 'units'
export interface Unit {
  key: UnitKey
  shift: number
}

const DIGITS = /^(-?)(\d+)(?:\.(\d+))?$/

/** Moves the decimal point of a decimal string `shift` places left: "412500000.00", 6 → "412.50000000". */
export function shiftLeft(amount: string, shift: number): string {
  const m = DIGITS.exec(amount)
  if (!m || shift === 0) return amount
  const [, sign, whole, fraction = ''] = m
  const padded = whole.padStart(shift + 1, '0')
  const head = padded.slice(0, padded.length - shift)
  return `${sign}${head}.${padded.slice(padded.length - shift)}${fraction}`
}

/** The unit that keeps the largest amount readable. */
export function unitFor(amounts: string[]): Unit {
  const digits = Math.max(0, ...amounts.map((a) => (DIGITS.exec(a)?.[2] ?? '').replace(/^0+/, '').length))
  if (digits >= 8) return { key: 'millions', shift: 6 }
  if (digits >= 6) return { key: 'thousands', shift: 3 }
  return { key: 'units', shift: 0 }
}

/** "412.5" in millions, "1,355.8"; signed when asked ("+11.8"). */
export function short(amount: string, unit: Unit, signed = false): string {
  const text = formatAmount(shiftLeft(amount, unit.shift), { fractionDigits: unit.shift ? 1 : 0 })
  return signed && !amount.startsWith('-') && !/^0*(\.0*)?$/.test(amount) ? `+${text}` : text
}

/** Σ of decimal strings, exact: summed as integer minor units, never as floats. */
export function sumAmounts(amounts: string[], digits = 2): string {
  const scale = 10n ** BigInt(digits)
  let total = 0n
  for (const amount of amounts) {
    const m = DIGITS.exec(amount)
    if (!m) continue
    const [, sign, whole, fraction = ''] = m
    const minor = BigInt(whole) * scale + BigInt((fraction + '0'.repeat(digits)).slice(0, digits) || '0')
    total += sign ? -minor : minor
  }
  const negative = total < 0n
  const abs = negative ? -total : total
  const text = `${abs / scale}.${(abs % scale).toString().padStart(digits, '0')}`
  return negative ? `-${text}` : text
}
