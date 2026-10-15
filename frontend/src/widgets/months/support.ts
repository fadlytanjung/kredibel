/** What supports a bank line (ADR-025), from the month run's state and the match's method. */

import type { BankLine } from '../../entities/bank-line'
import type { IconName } from '../../shared/ui'

export type Support = 'AUTO' | 'MANUAL' | 'PROPOSED' | 'NOT_REQUIRED' | 'EXCLUDED' | 'NO_SUPPORT' | 'NOT_RUN'

export const SUPPORT_CHIP: Record<Support, { chip: string; icon: IconName }> = {
  AUTO: { chip: 'auto', icon: 'link' },
  MANUAL: { chip: 'manual', icon: 'hand' },
  PROPOSED: { chip: 'proposed', icon: 'eye' },
  NOT_REQUIRED: { chip: 'cleared', icon: 'check' },
  EXCLUDED: { chip: 'excluded', icon: 'refresh' },
  NO_SUPPORT: { chip: 'none', icon: 'file-text' },
  NOT_RUN: { chip: 'none', icon: 'clock' },
}

/** The kinds whose chip carries a reason of its own (monthDetail.supportReason). */
export const REASONED: Support[] = ['PROPOSED', 'NOT_REQUIRED', 'EXCLUDED', 'NO_SUPPORT', 'NOT_RUN']

export function supportOf(line: BankLine): Support {
  switch (line.support) {
    case 'MATCHED':
      return line.match?.state === 'MANUAL' ? 'MANUAL' : 'AUTO'
    case 'PROPOSED':
    case 'NOT_REQUIRED':
    case 'EXCLUDED':
    case 'NO_SUPPORT':
      return line.support
    default:
      return 'NOT_RUN'
  }
}
