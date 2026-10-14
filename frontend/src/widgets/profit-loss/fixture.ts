/** Synthetic March reporting example matching design/mocks/profit-loss.html. */
import type { Accounts, ProfitLoss } from '../../entities/profit-loss'

const values: [string, string][] = [
  ['REVENUE', '120000000'],
  ['COST_OF_SALES', '72000000'],
  ['GROSS_PROFIT', '48000000'],
  ['OPERATING_EXPENSES', '18000000'],
  ['OPERATING_PROFIT', '30000000'],
  ['OTHER_INCOME', '1000000'],
  ['FINANCE_COSTS', '2000000'],
  ['INCOME_TAX', '3000000'],
  ['NET_PROFIT', '26000000'],
]

export const PNL: ProfitLoss = {
  period: '2026-03',
  months: ['2026-03'],
  currency: 'IDR',
  basis: 'ACCRUAL',
  coverage: 'IMPORTED_ENTRIES_ONLY',
  status: 'IMPORTED',
  inputCount: 14,
  classifiedCount: 14,
  lines: values.map(([id, amount]) => ({
    id,
    amount,
    factId: `fact:pnl_synthetic:${id}`,
    entryIds: ['entry_sales'],
  })),
  exclusions: {},
  gaps: [],
  entries: [
    {
      entryId: 'entry_sales',
      docId: 'doc_synthetic',
      rowNumber: 1,
      date: '2026-03-02',
      accountCode: '4000',
      accountName: 'Sales',
      pnlLine: 'REVENUE',
      subledger: 'RECEIVABLES',
      amount: '120000000',
    },
    {
      entryId: 'entry_cogs',
      docId: 'doc_synthetic_cogs',
      rowNumber: 2,
      date: '2026-03-05',
      accountCode: '5100',
      accountName: 'Purchases Wholesale',
      pnlLine: 'COST_OF_SALES',
      subledger: 'PAYABLES',
      amount: '72000000',
    },
    {
      entryId: 'entry_opex_payroll',
      docId: 'doc_synthetic_payroll',
      rowNumber: 3,
      date: '2026-03-25',
      accountCode: '6000',
      accountName: 'Salaries & Wages',
      pnlLine: 'OPERATING_EXPENSES',
      subledger: 'PAYROLL',
      amount: '18000000',
    },
    {
      entryId: 'entry_finance',
      docId: 'doc_synthetic_bank',
      rowNumber: 4,
      date: '2026-03-31',
      accountCode: '7100',
      accountName: 'Bank Interest & Fees',
      pnlLine: 'FINANCE_COSTS',
      subledger: 'CASH',
      amount: '4000000',
    },
  ],
}

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
