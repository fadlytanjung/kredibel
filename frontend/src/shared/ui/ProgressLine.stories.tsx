import type { Meta, StoryObj } from '@storybook/react'
import { ProgressLine } from './ProgressLine'

const meta: Meta<typeof ProgressLine> = {
  title: 'UI/ProgressLine',
  component: ProgressLine,
  tags: ['autodocs'],
}

export default meta
type Story = StoryObj<typeof ProgressLine>

export const ReadingPages: Story = {
  args: {
    current: 3,
    total: 18,
    status: 'running',
  },
}

export const MonthReconciling: Story = {
  args: {
    monthState: 'RECONCILING',
    status: 'running',
  },
}

export const MonthCollecting: Story = {
  args: {
    monthState: 'COLLECTING',
  },
}

export const MonthReconciled: Story = {
  args: {
    monthState: 'RECONCILED',
    status: 'done',
  },
}

export const PausedDailyLimit: Story = {
  args: {
    monthState: 'COLLECTING',
    status: 'paused',
    note: 'Reconciliation paused until tomorrow (daily limit)',
  },
}
