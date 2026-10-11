import type { Meta, StoryObj } from '@storybook/react'
import { MemoryRouter } from 'react-router-dom'
import { AppShell } from './AppShell'
import { EmptyState } from './EmptyState'
import { Button } from './Button'
import { Upload } from 'lucide-react'

const meta: Meta<typeof AppShell> = {
  title: 'UI/AppShell',
  component: AppShell,
  decorators: [
    (Story) => (
      <MemoryRouter initialEntries={['/']}>
        <Story />
      </MemoryRouter>
    ),
  ],
}

export default meta
type Story = StoryObj<typeof AppShell>

export const DesktopDashboard: Story = {
  parameters: {
    viewport: { defaultViewport: 'desktop' },
  },
  args: {
    children: (
      <div className="p-6">
        <EmptyState
          icon={<Upload className="w-6 h-6 text-brand" />}
          title="Upload your first documents"
          description="Drop bank statements, sales or purchase invoices to start reconciliation."
          action={<Button variant="primary">Upload Documents</Button>}
        />
      </div>
    ),
  },
}

export const TabletView: Story = {
  parameters: {
    viewport: { defaultViewport: 'tablet' },
  },
  args: {
    children: (
      <div className="p-4">
        <h1 className="text-xl font-bold mb-4">Tablet Navigation Rail</h1>
        <p className="text-ink-muted">AppShell seamlessly adapts to navigation rail.</p>
      </div>
    ),
  },
}

export const MobileView: Story = {
  parameters: {
    viewport: { defaultViewport: 'mobile' },
  },
  args: {
    children: (
      <div className="p-4">
        <h1 className="text-lg font-bold mb-3">Mobile Bottom Navigation</h1>
        <p className="text-ink-muted">AppShell renders bottom navigation dock on compact viewports.</p>
      </div>
    ),
  },
}
