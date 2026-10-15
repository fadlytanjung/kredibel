import { usePrefersReducedMotion } from '../lib/usePrefersReducedMotion'
import { Icon } from './Icon'

/**
 * The product's signature move (docs/12 §6.1, spec 020 AC-020-2): one printed figure with the two
 * independent reading marks and a double rule under the value. The marks converge on first paint
 * ("play"); under `prefers-reduced-motion` the scene is already settled. Meaning never depends on
 * the motion: the result is stated in text for screen readers either way.
 */
export interface ReadTwiceSceneProps {
  /** The printed figure the two readings agree on (already formatted). */
  figure: string
  aiLabel: string
  witnessLabel: string
  caption: string
  /** The result, for a screen reader and when motion is off (e.g. "agreed by two readings"). */
  resultLabel: string
  state?: 'play' | 'settled'
}

export function ReadTwiceScene({
  figure,
  aiLabel,
  witnessLabel,
  caption,
  resultLabel,
  state = 'play',
}: ReadTwiceSceneProps) {
  const reduced = usePrefersReducedMotion()
  const dataState = state === 'play' && !reduced ? 'play' : 'settled'

  return (
    <div>
      <div className="read-twice" data-state={dataState}>
        <span className="rt-mark ai">
          <Icon name="ai-reader" size="sm" />
          {aiLabel}
        </span>
        <span className="rt-value reading reading-agreed">{figure}</span>
        <span className="sr-only"> — {resultLabel}</span>
        <span className="rt-mark wit">
          <Icon name="text-layer" size="sm" />
          {witnessLabel}
        </span>
      </div>
      <p className="read-twice-caption">
        <span className="rt-dot" aria-hidden="true" />
        {caption}
      </p>
    </div>
  )
}
