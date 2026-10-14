import type { Meta, StoryObj } from '@storybook/react'
import { ReadTwiceScene } from './ReadTwiceScene'

const meta: Meta<typeof ReadTwiceScene> = {
  title: 'Public/ReadTwiceScene',
  component: ReadTwiceScene,
  args: {
    figure: '32,100,000',
    aiLabel: 'AI reader',
    witnessLabel: 'Witness',
    caption: 'read twice — the value is trusted only when both readings agree',
    resultLabel: 'agreed by two readings',
  },
}

export default meta
type Story = StoryObj<typeof ReadTwiceScene>

export const Play: Story = { args: { state: 'play' } }

export const Settled: Story = { args: { state: 'settled' } }
