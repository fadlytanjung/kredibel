import { useState } from 'react'
import { Button } from './Button'
import { Icon } from './Icon'

/**
 * The one live interaction on the landing (spec 018 AC-018-3): a possible copy is held, and choosing
 * "Same document" keeps the running total while "Different" counts it. This is the product's rule
 * (constitution P5): copies are recorded, never read, until a person decides. Client-side only.
 */
export interface DuplicateDecisionProps {
  title: string
  body: string
  sameLabel: string
  differentLabel: string
  sameResult: string
  differentResult: string
  totalLabel: string
  baseTotal: string
  countedTotal: string
}

export function DuplicateDecision({
  title,
  body,
  sameLabel,
  differentLabel,
  sameResult,
  differentResult,
  totalLabel,
  baseTotal,
  countedTotal,
}: DuplicateDecisionProps) {
  const [choice, setChoice] = useState<'same' | 'different' | null>(null)
  const counted = choice === 'different'

  return (
    <div className="decision">
      <p className="decision-head">
        <Icon name="copy" size="sm" />
        {title}
      </p>
      <p className="muted">{body}</p>
      <div className="decision-actions">
        <Button
          variant={choice === 'same' ? 'primary' : 'secondary'}
          aria-pressed={choice === 'same'}
          onClick={() => setChoice('same')}
        >
          {sameLabel}
        </Button>
        <Button
          variant={choice === 'different' ? 'primary' : 'secondary'}
          aria-pressed={choice === 'different'}
          onClick={() => setChoice('different')}
        >
          {differentLabel}
        </Button>
      </div>
      <div className="statement-foot">
        <span>{totalLabel}</span>
        <span className="total">{counted ? countedTotal : baseTotal}</span>
      </div>
      <p
        className={`decision-result${choice === 'same' ? ' ok' : choice === 'different' ? ' counted' : ''}`}
        role="status"
        aria-live="polite"
      >
        {choice === 'same' && (
          <>
            <Icon name="check" size="sm" />
            {sameResult}
          </>
        )}
        {choice === 'different' && (
          <>
            <Icon name="circle-alert" size="sm" />
            {differentResult}
          </>
        )}
      </p>
    </div>
  )
}
