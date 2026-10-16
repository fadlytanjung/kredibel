/** Synthetic report shared with the HTML mock (AC-018-7). */
import type { Accounts, ProfitLoss } from '../../entities/profit-loss'
import report from '../../../../contracts/design/fixtures/profit-loss.json' with { type: 'json' }
import cashAccounts from '../../../../contracts/design/fixtures/profit-loss-cash-accounts.json' with { type: 'json' }
import cashReport from '../../../../contracts/design/fixtures/profit-loss-cash.json' with { type: 'json' }
import lossReport from '../../../../contracts/design/fixtures/profit-loss-loss.json' with { type: 'json' }

export const PNL = report as ProfitLoss
/** The same workspace before any ledger export: a cash basis from its bank lines (AC-018-8). */
export const PNL_CASH = cashReport as ProfitLoss
export const PNL_CASH_ACCOUNTS = cashAccounts as Accounts
/** A half month with a net loss: the flow draws the loss as a source (docs/11 §6.2). */
export const PNL_LOSS = lossReport as unknown as ProfitLoss

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
