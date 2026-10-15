/** Exact reporting values; Number conversion belongs only in the drawing geometry. */
import type { ProfitLoss } from '../../entities/profit-loss'
import { sumAmounts } from '../../shared/lib/units'

export interface ProfitNode {
  id: string
  label: string
  amount: string
  role: 'src' | 'acc' | 'use' | 'operating' | 'kept'
  entries: ProfitLoss['entries']
}

export function profitFlow(report: ProfitLoss, label: (key: string) => string) {
  const byLine = (id: string) => report.lines.find((line) => line.id === id)
  const value = (id: string) => byLine(id)?.amount ?? '0'
  const entriesFor = (id: string) => report.entries.filter((entry) => byLine(id)?.entryIds.includes(entry.entryId))
  const sources: ProfitNode[] = []
  const uses: ProfitNode[] = []
  const revenue = report.entries.filter((entry) => entry.pnlLine === 'REVENUE')
  for (const account of [...new Set(revenue.map((entry) => entry.accountCode))].sort()) {
    const entries = revenue.filter((entry) => entry.accountCode === account)
    sources.push({ id: `account:${account}`, label: `${account} ${entries[0].accountName}`, amount: sumAmounts(entries.map((entry) => entry.amount)), role: 'src', entries })
  }
  sources.push({ id: 'OTHER_INCOME', label: label('lines.OTHER_INCOME'), amount: value('OTHER_INCOME'), role: 'src', entries: entriesFor('OTHER_INCOME') })
  const add = (id: string, role: ProfitNode['role']) => uses.push({ id, label: label(`lines.${id}`), amount: value(id), role, entries: entriesFor(id) })
  add('COST_OF_SALES', 'use')
  const operating = report.entries.filter((entry) => entry.pnlLine === 'OPERATING_EXPENSES')
  for (const subledger of [...new Set(operating.map((entry) => entry.subledger))].sort()) {
    const entries = operating.filter((entry) => entry.subledger === subledger)
    uses.push({ id: `subledger:${subledger}`, label: label(`subledgers.${subledger}`), amount: sumAmounts(entries.map((entry) => entry.amount)), role: 'operating', entries })
  }
  add('FINANCE_COSTS', 'operating')
  add('INCOME_TAX', 'operating')
  add('NET_PROFIT', 'kept')
  const amount = sumAmounts([value('REVENUE'), value('OTHER_INCOME')])
  const matches = (a: string[], b: string) => sumAmounts(a) === sumAmounts([b])
  // Sankey bands cannot represent negative weights. Signed rows preserve loss/reversal values.
  if ([...sources, ...uses].some((node) => node.amount.startsWith('-')) ||
      amount === '0.00' ||
      !matches(revenue.map((entry) => entry.amount), value('REVENUE')) ||
      !matches(operating.map((entry) => entry.amount), value('OPERATING_EXPENSES')) ||
      !matches(uses.map((node) => node.amount), amount)) return null
  return {
    sources: sources.filter((node) => sumAmounts([node.amount]) !== '0.00'),
    uses: uses.filter((node) => sumAmounts([node.amount]) !== '0.00'),
    income: { id: 'income', label: label('totalIncome'), amount, role: 'acc' as const, entries: report.entries.filter((entry) => ['REVENUE', 'OTHER_INCOME'].includes(entry.pnlLine)) },
  }
}
