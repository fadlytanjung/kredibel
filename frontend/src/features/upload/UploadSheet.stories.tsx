import type { Meta, StoryObj } from '@storybook/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { UploadSheet } from './UploadSheet'

const queryClient = new QueryClient()

const meta: Meta<typeof UploadSheet> = {
  title: 'Features/UploadSheet',
  component: UploadSheet,
  decorators: [
    (Story) => (
      <MemoryRouter>
        <QueryClientProvider client={queryClient}>
          <div className="max-w-3xl p-6">
            <Story />
          </div>
        </QueryClientProvider>
      </MemoryRouter>
    ),
  ],
}

export default meta
type Story = StoryObj<typeof UploadSheet>

export const Default: Story = {}

export const WithUploadItem: Story = {
  render: () => <UploadSheet />,
}
