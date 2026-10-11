import type { Meta, StoryObj } from '@storybook/react'
import { Button } from './Button'
import { Panel } from './Panel'

const meta: Meta<typeof Panel> = {
  title: 'UI/Panel',
  component: Panel,
  tags: ['autodocs'],
  argTypes: { padded: { control: 'boolean' } },
}

export default meta
type Story = StoryObj<typeof Panel>

export const Plain: Story = {
  args: { children: 'A kit panel with its standard padding.', padded: true },
}

export const WithHeadAndAction: Story = {
  args: {
    title: 'Needs you',
    action: (
      <Button size="sm" variant="secondary">
        All 9
      </Button>
    ),
    children: 'Items that only a person can settle.',
    padded: true,
  },
}
