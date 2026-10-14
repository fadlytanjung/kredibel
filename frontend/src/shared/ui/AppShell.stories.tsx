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
      <MemoryRouter initialEntries={['/dashboard']}>
        <Story />
      </MemoryRouter>
    ),
  ],
}

export default meta
type Story = StoryObj<typeof AppShell>

// Synthetic sample data; the real shell gets these from the workspace API.
const sample = {
  user: { name: 'Demo Owner', role: 'owner' },
  workspace: { name: 'Sunrise Coffee Roasters', subtitle: 'COMPANY · IDR · IFRS' },
  trial: { status: 'TRIALING' as const, daysLeft: 23, pagesUsed: 286, pagesMax: 400 },
  counts: { documents: 92, review: 9, risk: 2 },
}

export const DesktopDashboard: Story = {
  parameters: {
    viewport: { defaultViewport: 'desktop' },
  },
  args: {
    ...sample,
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
    ...sample,
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
    ...sample,
    children: (
      <div className="p-4">
        <h1 className="text-lg font-bold mb-3">Mobile Bottom Navigation</h1>
        <p className="text-ink-muted">AppShell renders bottom navigation dock on compact viewports.</p>
      </div>
    ),
  },
}
