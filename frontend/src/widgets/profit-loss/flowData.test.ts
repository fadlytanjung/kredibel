import { describe, expect, it } from 'vitest'
import { profitFlow } from './flowData'
import { PNL, PNL_LOSS } from './fixture'

const label = (key: string) => key

describe('the profit and loss flow (spec 018, AC-018-5)', () => {
  it('a profit: income meets in the middle and splits into expenses and the profit kept', () => {
    const flow = profitFlow(PNL, label)!
    expect(flow.loss).toBe(false)
    expect(flow.income).toMatchObject({ label: 'totalIncome', amount: '121000000.00' })
    expect(flow.uses.at(-1)).toMatchObject({ id: 'NET_PROFIT', role: 'kept', amount: '26000000' })
  })

  it('a net loss is drawn as a source that funds the expenses the income did not', () => {
    const flow = profitFlow(PNL_LOSS, label)!
    expect(flow.loss).toBe(true)
    expect(flow.sources.map((n) => [n.id, n.amount])).toEqual([
      ['account:4000', '40000000.00'],
      ['OTHER_INCOME', '1000000'],
      ['NET_LOSS', '15000000'],
    ])
    expect(flow.income).toMatchObject({ label: 'totalCosts', amount: '56000000.00' })
    expect(flow.uses.map((n) => n.id)).toEqual(['COST_OF_SALES', 'subledger:PAYROLL', 'FINANCE_COSTS'])
  })

  it('a reversal (a negative expense) cannot be a band: the signed rows stay', () => {
    const reversed = {
      ...PNL,
      lines: PNL.lines.map((l) => (l.id === 'FINANCE_COSTS' ? { ...l, amount: '-2000000' } : l)),
    }
    expect(profitFlow(reversed, label)).toBeNull()
  })
})
