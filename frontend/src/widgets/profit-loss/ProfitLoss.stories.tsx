import type { Meta, StoryObj } from '@storybook/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import '../../shared/i18n/setup'
import { EMPTY_PNL, PNL, PNL_CASH } from './fixture'
import { ProfitLossPanel, ProfitLossView } from './ProfitLossPanel'

const meta: Meta<typeof ProfitLossView> = {
  title: 'Dashboard/ProfitLoss', component: ProfitLossView, args: { report: PNL },
  decorators: [(Story) => <MemoryRouter><div className="page"><Story /></div></MemoryRouter>],
}
export default meta
type Story = StoryObj<typeof ProfitLossView>
export const Default: Story = {}
export const Mobile: Story = { parameters: { viewport: { defaultViewport: 'mobile' } } }
export const Tablet: Story = { parameters: { viewport: { defaultViewport: 'tablet' } } }
export const Desktop: Story = { parameters: { viewport: { defaultViewport: 'desktop' } } }
export const Empty: Story = { args: { report: EMPTY_PNL } }
export const CashBasis: Story = { name: 'Cash basis (no ledger export)', args: { report: PNL_CASH } }
export const Partial: Story = { args: { report: { ...PNL, status: 'PARTIAL', exclusions: { UNCLASSIFIED: 2 }, gaps: ['UNBALANCED_JOURNAL'] } } }
export const Loading: Story = { render: () => <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { queryFn: () => new Promise(() => {}), enabled: false } } })}><ProfitLossPanel period="all" /></QueryClientProvider> }
export const FailedRequest: Story = { name: 'Error', render: () => {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, enabled: false } } })
  const query = client.getQueryCache().build(client, { queryKey: ['profit-loss', 'all'] })
  query.setState({ status: 'error', error: new Error('offline') })
  return <QueryClientProvider client={client}><ProfitLossPanel period="all" /></QueryClientProvider>
} }

export const Loss: Story = { args: { report: { ...PNL, currency: 'USD', lines: PNL.lines.map((line) => line.id === 'NET_PROFIT' ? { ...line, amount: '-10.25' } : line) } } }
