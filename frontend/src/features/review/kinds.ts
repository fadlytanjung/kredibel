import { formatMonth } from '../../shared/lib/formatDate'
import type { IconName } from '../../shared/ui'

/** The tile of each kind of review item (docs/11 §6.5). */
export const KIND_ICON: Record<string, IconName> = {
  POSSIBLE_DUPLICATE: 'copy',
  PROPOSED_MATCH: 'link',
  UNMATCHED_DOCUMENT: 'file-text',
  UNMATCHED_BANK_LINE: 'bank',
  LOW_CONFIDENCE_VALUE: 'eye',
  LEDGER_DIFFERENCE: 'scale',
  CONFIRM_TYPE: 'tag',
  CONFIRM_LEDGER_MAPPING: 'table',
}

export const monthName = (month: string) => formatMonth(month, 'long')
