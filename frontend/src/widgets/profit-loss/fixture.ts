/** Synthetic report shared with the HTML mock (AC-018-7). */
import type { Accounts, ProfitLoss } from '../../entities/profit-loss'
import report from '../../../../contracts/design/fixtures/profit-loss.json' with { type: 'json' }

export const PNL = report as ProfitLoss

export const EMPTY_PNL: ProfitLoss = {
  ...PNL,
  status: 'UNAVAILABLE',
  inputCount: 0,
  classifiedCount: 0,
  lines: PNL.lines.map((line) => ({ ...line, amount: null, entryIds: [] })),
  entries: [],
}

export const PNL_ACCOUNTS: Accounts = {
  accounts: [
    {
      accountCode: '4000',
      accountName: 'Sales',
      classification: {
        accountCode: '4000',
        pnlLine: 'REVENUE',
        subledger: 'RECEIVABLES',
      },
    },
  ],
  pnlLines: { REVENUE: 'Revenue', BALANCE_SHEET: 'Balance sheet (excluded from profit)' },
  subledgers: { RECEIVABLES: 'Receivables', GENERAL: 'General journals' },
}
