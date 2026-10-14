import type { Meta, StoryObj } from '@storybook/react'
import { CopyEmailButton } from './CopyEmailButton'
import { DepthStage } from './DepthStage'
import { FlowRibbon } from './FlowRibbon'
import { Lamp } from './Lamp'
import { PaperArtefact } from './PaperArtefact'
import { ScrollStory } from './ScrollStory'

// The public site's depth scenes (spec 018, docs/12 §12). They read the `--pub-*` variables set on
// `.site`, so every story renders inside the public frame.
const meta: Meta = {
  title: 'Public/Scenes',
  decorators: [
    (Story) => (
      <div className="viewport">
        <div className="site">
          <Story />
        </div>
      </div>
    ),
  ],
}

export default meta
type Story = StoryObj

export const DeckOnInk: Story = {
  render: () => (
    <Lamp className="pub-section pub-hero">
      <div className="pub-hero-scene">
        <DepthStage deck={['ledger', 'invoice', 'receipt', 'statement', 'receipt']}>
          <PaperArtefact kind="statement" stamp="checked" />
        </DepthStage>
      </div>
    </Lamp>
  ),
}

export const Artefacts: Story = {
  render: () => (
    <Lamp className="pub-section">
      <div className="pub-inner pub-band">
        <PaperArtefact kind="statement" />
        <PaperArtefact kind="invoice" />
        <PaperArtefact kind="receipt" />
        <PaperArtefact kind="ledger" stamp="held" />
      </div>
    </Lamp>
  ),
}

export const MoneyFlowRibbons: Story = {
  render: () => (
    <Lamp className="pub-section">
      <div className="pub-inner">
        <FlowRibbon legend={{ in: 'Money in', out: 'Money out', flagged: 'Paid to a new account' }} />
      </div>
    </Lamp>
  ),
}

export const Story4Chapters: Story = {
  render: () => (
    <ScrollStory
      eyebrow="Inside the reading room"
      title="Watch one month get checked."
      lead="Four things happen to every document you upload."
      chapters={[
        { key: 'a', title: 'It arrives in any order', body: 'Statements, invoices, receipts and the ledger.' },
        { key: 'b', title: 'Every page is read twice', body: 'A value counts only when both readings agree.' },
        { key: 'c', title: 'Code checks it', body: 'The lamp lands on the printed figure.' },
        { key: 'd', title: 'The month reconciles itself', body: 'What AI cannot settle waits for you.' },
      ]}
      stage={
        <>
          <div className="rr-sheet rr-s1">
            <PaperArtefact kind="statement" />
          </div>
          <div className="rr-sheet rr-s2">
            <PaperArtefact kind="invoice" />
          </div>
        </>
      }
    />
  ),
}

export const CopyAddress: Story = {
  render: () => (
    <Lamp className="pub-section">
      <div className="pub-letter-actions">
        <CopyEmailButton email="hello@kredibel.app" label="Copy address" copied="Address copied." failed="Could not copy." />
      </div>
    </Lamp>
  ),
}
