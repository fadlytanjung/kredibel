import type { Meta, StoryObj } from '@storybook/react'
import { Panel } from './Panel'
import { Button } from './Button'

const meta: Meta<typeof Panel> = {
  title: 'UI/Panel',
  component: Panel,
  tags: ['autodocs'],
  argTypes: {
    elevation: {
      control: 'select',
      options: ['flat', 'raised', 'overlay'],
    },
    padded: {
      control: 'boolean',
    },
  },
}

export default meta
type Story = StoryObj<typeof Panel>

export const Flat: Story = {
  args: {
    title: 'Panel Header',
    children: 'This is the main panel content area.',
    elevation: 'flat',
    padded: true,
  },
}

export const RaisedWithAction: Story = {
  args: {
    title: 'Financial Summary',
    action: <Button size="sm" variant="secondary">Refresh</Button>,
    children: 'Detailed ledger and reconciliation statistics.',
    elevation: 'raised',
    padded: true,
  },
}
