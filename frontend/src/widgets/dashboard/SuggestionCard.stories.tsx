import type { Meta, StoryObj } from '@storybook/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import counterparties from '../../../../contracts/design/fixtures/counterparties.json' with { type: 'json' }
import '../../shared/i18n/setup'
import type { Suggestion } from '../../entities/counterparty'
import { SuggestionCard } from './SuggestionCard'

const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })

const meta: Meta<typeof SuggestionCard> = {
  title: 'Widgets/Dashboard/SuggestionCard',
  component: SuggestionCard,
  decorators: [
    (Story) => (
      <QueryClientProvider client={client}>
        <MemoryRouter>
          <div style={{ maxWidth: 420 }}>{/* allow-raw-style: story canvas width */}
            <Story />
          </div>
        </MemoryRouter>
      </QueryClientProvider>
    ),
  ],
}
export default meta

type Story = StoryObj<typeof SuggestionCard>

/** Two details found in the documents, each with a decision (spec 014, AC-014-7). */
export const Found: Story = { args: { items: counterparties.suggestions as Suggestion[] } }

/** One of them contradicts the profile: both values are shown (AC-014-6). */
export const Conflict: Story = {
  args: {
    items: [
      { ...(counterparties.suggestions[0] as Suggestion), status: 'CONFLICT', conflictWith: '••••.111' },
    ],
  },
}

/** Nothing open: the card renders nothing. */
export const Nothing: Story = { args: { items: [] } }
