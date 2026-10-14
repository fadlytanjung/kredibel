import type { Meta, StoryObj } from '@storybook/react'
import { DuplicateDecision } from './DuplicateDecision'

const meta: Meta<typeof DuplicateDecision> = {
  title: 'Public/DuplicateDecision',
  component: DuplicateDecision,
  args: {
    title: 'The same statement, uploaded again',
    body: 'Looks like ACB_Feb_2026.pdf, same bank, period and closing balance. It is held until you decide.',
    sameLabel: 'Same document',
    differentLabel: 'Different',
    sameResult: 'Kept as a copy. Not read again and not counted.',
    differentResult: 'Counted as a second statement.',
    totalLabel: 'Statement total',
    baseTotal: '18,703,918',
    countedTotal: '24,300,000',
  },
}

export default meta
type Story = StoryObj<typeof DuplicateDecision>

export const Default: Story = {}
