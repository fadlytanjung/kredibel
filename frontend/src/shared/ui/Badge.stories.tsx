import type { Meta, StoryObj } from '@storybook/react'
import { Badge } from './Badge'

const meta: Meta<typeof Badge> = {
  title: 'UI/Badge',
  component: Badge,
  tags: ['autodocs'],
  argTypes: {
    variant: {
      control: 'select',
      options: ['default', 'critical', 'high', 'medium', 'low', 'clean', 'tampered', 'brand', 'evidence', 'outline'],
    },
  },
}

export default meta
type Story = StoryObj<typeof Badge>

export const Default: Story = {
  args: {
    children: 'Badge Default',
    variant: 'default',
  },
}

export const Critical: Story = {
  args: {
    children: 'Critical Risk',
    variant: 'critical',
  },
}

export const Clean: Story = {
  args: {
    children: 'Clean Verdict',
    variant: 'clean',
  },
}

export const Brand: Story = {
  args: {
    children: 'Trial Plan',
    variant: 'brand',
  },
}
