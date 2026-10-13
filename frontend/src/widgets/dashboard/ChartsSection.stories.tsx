import type { Meta, StoryObj } from '@storybook/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import '../../shared/i18n/setup'
import { CASH, FLOW_PARTIES, FLOW_STATEMENT, LINES } from './charts.fixture'
import { ChartsSection } from './ChartsSection'

function seeded(cashData = CASH) {
  const client = new QueryClient({ defaultOptions: { queries: { staleTime: Infinity, retry: false } } })
  client.setQueryData(['money-flow', { period: 'all', view: 'STATEMENT', framework: 'IFRS' }], FLOW_STATEMENT)
  client.setQueryData(['money-flow', { period: 'all', view: 'COUNTERPARTIES', framework: 'IFRS' }], FLOW_PARTIES)
  client.setQueryData(['money-flow', { period: 'all', view: 'STATEMENT', framework: 'US_GAAP' }], FLOW_STATEMENT)
  client.setQueryData(['money-flow', { period: 'all', view: 'COUNTERPARTIES', framework: 'US_GAAP' }], FLOW_PARTIES)
  client.setQueryData(['cash-flow', { period: 'all', framework: 'IFRS' }], cashData)
  client.setQueryData(['cash-flow', { period: 'all', framework: 'US_GAAP' }], cashData)
  client.setQueryData(
    ['flow-lines', { flow: 'src:client:harbor>acc:acb', period: 'all', view: 'STATEMENT', framework: 'IFRS' }],
    LINES,
  )
  return client
}

const meta: Meta<typeof ChartsSection> = {
  title: 'Dashboard/ChartsSection',
  component: ChartsSection,
  args: {
    period: 'all',
    range: 'February to April 2026',
    framework: 'IFRS',
  },
  decorators: [
    (Story) => (
      <MemoryRouter>
        <QueryClientProvider client={seeded()}>
          <div className="dash p-6">
            <Story />
          </div>
        </QueryClientProvider>
      </MemoryRouter>
    ),
  ],
}

export default meta
type Story = StoryObj<typeof ChartsSection>

export const Desktop: Story = {
  parameters: {
    viewport: { defaultViewport: 'desktop' },
  },
}

export const Tablet: Story = {
  parameters: {
    viewport: { defaultViewport: 'tablet' },
  },
}

export const Mobile: Story = {
  parameters: {
    viewport: { defaultViewport: 'mobile' },
  },
}

export const UnbalancedWaterfall: Story = {
  parameters: {
    viewport: { defaultViewport: 'desktop' },
  },
  decorators: [
    (Story) => (
      <MemoryRouter>
        <QueryClientProvider
          client={seeded({
            ...CASH,
            balanced: false,
            gaps: [{ kind: 'MISSING_MONTH', month: '2026-03', account: 'Archipelago Commerce Bank ••••4821' }],
          })}
        >
          <div className="dash p-6">
            <Story />
          </div>
        </QueryClientProvider>
      </MemoryRouter>
    ),
  ],
}
