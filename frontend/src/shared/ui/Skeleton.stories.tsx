import type { Meta, StoryObj } from '@storybook/react'
import { Skeleton } from './Skeleton'

const meta: Meta<typeof Skeleton> = {
  title: 'UI/Skeleton',
  component: Skeleton,
  tags: ['autodocs'],
  argTypes: {
    variant: {
      control: 'select',
      options: ['text', 'rectangular', 'circular'],
    },
  },
}

export default meta
type Story = StoryObj<typeof Skeleton>

export const Text: Story = {
  args: {
    variant: 'text',
    className: 'w-48',
  },
}

export const Rectangular: Story = {
  args: {
    variant: 'rectangular',
    className: 'w-64 h-32',
  },
}

export const Circular: Story = {
  args: {
    variant: 'circular',
    className: 'w-12 h-12',
  },
}
