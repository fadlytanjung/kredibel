/**
 * Exact sums of decimal strings, the JSON form of money (docs/09 §2): amounts are added as
 * integers of their smallest digit, so no amount ever passes through a float.
 */

const DECIMAL = /^(-?)(\d+)(?:\.(\d+))?$/

export function sumDecimals(values: string[]): string {
  const parsed = values.map((value) => DECIMAL.exec(value)).filter((m): m is RegExpExecArray => m !== null)
  const scale = Math.max(2, ...parsed.map((m) => (m[3] ?? '').length))
  let total = 0n
  for (const [, sign, whole, fraction = ''] of parsed) {
    const units = BigInt(whole + fraction.padEnd(scale, '0'))
    total += sign ? -units : units
  }
  const negative = total < 0n
  const digits = (negative ? -total : total).toString().padStart(scale + 1, '0')
  return `${negative ? '-' : ''}${digits.slice(0, -scale)}.${digits.slice(-scale)}`
}
