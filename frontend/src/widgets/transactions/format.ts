import type { IconName } from '../../shared/ui/icons.generated'

/** The match chip of each state, as the month page draws a line's support. */
export const MATCH_CHIP: Record<string, { chip: string; icon: IconName }> = {
  AUTO: { chip: 'auto', icon: 'link' },
  MANUAL: { chip: 'manual', icon: 'hand' },
  PROPOSED: { chip: 'proposed', icon: 'eye' },
  UNMATCHED: { chip: 'none', icon: 'file-text' },
  EXCLUDED: { chip: 'excluded', icon: 'refresh' },
}

export const READING_MARK: Record<string, string> = {
  AGREED: 'reading-agreed',
  SINGLE_SOURCE: 'reading-single',
  CONFLICT: 'reading-conflict',
  MISSING: 'reading-conflict',
}

export const RECORD_ICON: Record<string, IconName> = { INVOICE: 'file-text', RECEIPT: 'receipt', LEDGER_ENTRY: 'book' }
