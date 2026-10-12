/** How a statement line was read, and which way its money went (spec 005, T005-11). */

import type { BankLine, ValueReading } from './api'

type Status = ValueReading['status']

const RANK: Record<string, number> = { AGREED: 0, SINGLE_SOURCE: 1, CONFLICT: 2, MISSING: 3 }

/** The weakest reading among a line's values. */
export function lineStatus(line: BankLine): Status {
  const statuses = Object.values(line.readings ?? {}).map((r) => r.status)
  return statuses.reduce<Status>((worst, s) => ((RANK[s] ?? 0) > (RANK[worst] ?? 0) ? s : worst), 'AGREED')
}

/** Where to point on the page: the amount's box, else the description's. */
export function lineBox(line: BankLine) {
  return line.readings?.amount?.bbox ?? line.readings?.description?.bbox
}

export function isIncoming(line: BankLine): boolean {
  return !line.amount.amount.startsWith('-')
}

/** A line a person should look at: a value one source missed, or the readings differ. */
export function needsCheck(line: BankLine): boolean {
  return line.source === 'WITNESS' || lineStatus(line) !== 'AGREED'
}
