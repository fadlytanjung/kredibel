/** The column mapping's rules, shared by the editor and the panel (spec 005, AC-005-11). */

import type { LedgerMapping } from '../../entities/document'

export const DATE_FORMATS = ['DD/MM/YYYY', 'MM/DD/YYYY', 'YYYY-MM-DD', 'DD-MM-YYYY', 'DD.MM.YYYY']

/** The same rule as the API's validation: the required columns and one amount layout. */
export function isComplete(mapping: LedgerMapping): boolean {
  const two = Boolean(mapping.debit && mapping.credit)
  const one = Boolean(mapping.amount)
  const half = Boolean(mapping.debit) !== Boolean(mapping.credit)
  return Boolean(mapping.date && mapping.description && mapping.accountCode) && two !== one && !half
}
