import type { Meta, StoryObj } from '@storybook/react'
import { useState } from 'react'
import { SegmentedControl } from './SegmentedControl'

const meta: Meta<typeof SegmentedControl> = {
  title: 'UI/SegmentedControl',
  component: SegmentedControl,
  tags: ['autodocs'],
}

export default meta
type Story = StoryObj<typeof SegmentedControl>

function ViewsDemo() {
  const [val, setVal] = useState('flow')
  return (
    <SegmentedControl
      ariaLabel="Money flow view"
      value={val}
      onChange={setVal}
      options={[
        { key: 'flow', label: 'Flow' },
        { key: 'bars', label: 'Bars' },
        { key: 'table', label: 'Table' },
        { key: 'parties', label: 'By client and supplier' },
      ]}
    />
  )
}

function FrameworksDemo() {
  const [val, setVal] = useState('IFRS')
  return (
    <SegmentedControl
      ariaLabel="Accounting framework"
      value={val}
      onChange={setVal}
      options={[
        { key: 'IFRS', label: 'IFRS' },
        { key: 'US_GAAP', label: 'US GAAP' },
      ]}
    />
  )
}

export const Views: Story = {
  render: () => <ViewsDemo />,
}

export const Frameworks: Story = {
  render: () => <FrameworksDemo />,
}
