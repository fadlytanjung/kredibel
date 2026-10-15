import type { Meta, StoryObj } from '@storybook/react'
import { MemoryRouter } from 'react-router-dom'
import '../../shared/i18n/setup'
import type { Alert, FlowNode, Kpi, MonthSummary } from '../../entities/insight'
import { AlertList } from './AlertList'
import { FlowSummary } from './FlowSummary'
import { KpiCard } from './KpiCard'
import { MonthStrip } from './MonthStrip'

// Synthetic data only (non-negotiable 7).
const money = (amount: string) => ({ amount, currency: 'IDR' })
const KPIS: Kpi[] = [
  { id: 'MONEY_IN', value: money('1355800000.00'), previous: money('1201000000.00') },
  { id: 'MONEY_OUT', value: money('1286800000.00'), previous: money('1190000000.00') },
  { id: 'NET', value: money('69000000.00'), previous: null },
  { id: 'AUTO_MATCH_RATE', value: '0.8960', previous: '0.8700' },
  { id: 'DOCUMENTS_WAITING', value: 4, previous: null },
]
const MONTHS: MonthSummary[] = [
  { month: '2026-01', state: 'RECONCILED', statementsPresent: 1, statementsExpected: 1, autoMatchRate: '0.9400', riskLevel: 'LOW' },
  { month: '2026-02', state: 'NEEDS_REVIEW', statementsPresent: 1, statementsExpected: 1, autoMatchRate: '0.8900', riskLevel: 'MEDIUM' },
  { month: '2026-03', state: 'NEEDS_REVIEW', statementsPresent: 1, statementsExpected: 1, autoMatchRate: '0.8600', riskLevel: 'CRITICAL' },
  { month: '2026-04', state: 'COLLECTING', statementsPresent: 0, statementsExpected: 1 },
]
const ALERTS: Alert[] = [
  { severity: 'CRITICAL', title: 'March statement edited after the bank issued it', month: '2026-03', findingId: 'fnd_1', link: '/risk/fnd_1' },
  { severity: 'HIGH', title: 'Roastline Equipment Service paid to a new account', month: '2026-05', findingId: 'fnd_2', link: '/risk/fnd_2' },
]
const SOURCES: FlowNode[] = [
  { id: 'src:client:cp_1', column: 'SOURCE', label: 'Daybreak Cafe', value: money('412000000.00') },
  { id: 'src:client:cp_2', column: 'SOURCE', label: 'Harborview Hotel Group', value: money('301500000.00') },
  { id: 'src:cash', column: 'SOURCE', label: 'Cash sales deposited', value: money('96400000.00') },
]
const USES: FlowNode[] = [
  { id: 'line:COST_OF_SALES', column: 'LINE', label: 'Cost of sales', value: money('564000000.00') },
  { id: 'line:OPERATING_EXPENSES:PAYROLL', column: 'LINE', label: 'Payroll', value: money('288000000.00') },
  { id: 'line:OPERATING_EXPENSES:RENT', column: 'LINE', label: 'Rent', value: money('90000000.00') },
]

const meta: Meta = {
  title: 'Dashboard/Widgets',
  decorators: [
    (Story) => (
      <MemoryRouter>
        <div className="page">
          <div className="dash">
            <Story />
          </div>
        </div>
      </MemoryRouter>
    ),
  ],
}

export default meta
type Story = StoryObj

export const Figures: Story = {
  render: () => (
    <section className="ledger">
      <dl className="ledger-figures">
        {KPIS.map((kpi) => (
          <KpiCard key={kpi.id} kpi={kpi} />
        ))}
      </dl>
    </section>
  ),
}

export const Risk: Story = { render: () => <AlertList alerts={ALERTS} /> }
export const NoRisk: Story = { render: () => <AlertList alerts={[]} /> }
export const WhereTheMoneyWent: Story = { render: () => <FlowSummary sources={SOURCES} uses={USES} /> }
export const Months: Story = { render: () => <MonthStrip months={MONTHS} /> }
