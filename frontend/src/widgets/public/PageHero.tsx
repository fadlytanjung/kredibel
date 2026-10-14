import type { ReactNode } from 'react'
import { DepthStage } from './DepthStage'
import { Lamp } from './Lamp'

/**
 * The ink hero of an inner public page (spec 018, AC-018-6; docs/12 §12): eyebrow, the page's one
 * h1, a lead, and on wide screens a small depth scene (by default a deck of paper artefacts).
 */
export interface PageHeroProps {
  eyebrow: string
  title: string
  lead?: string
  children?: ReactNode
  art?: ReactNode
}

export function PageHero({ eyebrow, title, lead, children, art }: PageHeroProps) {
  return (
    <Lamp className="pub-page-hero">
      <div className="pub-inner pub-page-hero-inner">
        <div className="pub-page-hero-copy">
          <p className="pub-eyebrow">{eyebrow}</p>
          <h1 className="pub-page-title">{title}</h1>
          {lead && <p className="pub-lead">{lead}</p>}
          {children}
        </div>
        <div className="pub-page-hero-art" aria-hidden="true">
          {art ?? <DepthStage deck={['ledger', 'invoice', 'statement']} />}
        </div>
      </div>
    </Lamp>
  )
}
