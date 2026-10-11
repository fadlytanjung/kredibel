import type { Meta, StoryObj } from '@storybook/react'
import { EmptyState } from './EmptyState'
import { Button } from './Button'
import { Upload } from 'lucide-react'

const meta: Meta<typeof EmptyState> = {
  title: 'UI/EmptyState',
  component: EmptyState,
  tags: ['autodocs'],
}

export default meta
type Story = StoryObj<typeof EmptyState>

export const Default: Story = {
  args: {
    icon: <Upload className="w-6 h-6 text-brand" />,
    title: 'Upload your first documents',
    description: 'Drop statements, invoices or receipts to begin reconciling books automatically.',
    action: <Button variant="primary">Upload Documents</Button>,
  },
}
