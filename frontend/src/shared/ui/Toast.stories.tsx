import type { Meta, StoryObj } from '@storybook/react'
import { Toast } from './Toast'
import { CheckCircle2 } from 'lucide-react'

const meta: Meta<typeof Toast> = {
  title: 'UI/Toast',
  component: Toast,
  tags: ['autodocs'],
}

export default meta
type Story = StoryObj<typeof Toast>

export const Success: Story = {
  args: {
    message: 'Reconciliation run completed successfully.',
    icon: <CheckCircle2 className="w-5 h-5 text-clean" />,
    onClose: () => {},
  },
}
