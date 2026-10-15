import { useRef } from 'react'
import { useInViewAttr } from '../../shared/lib/useInViewAttr'

/**
 * Money-flow ribbons that draw themselves as they arrive (spec 020, AC-020-4; docs/12 §12): money in
 * gathers into the account and leaves for suppliers, payroll and tax, with one payment to a new
 * account lit by the lamp. Decorative — the words are in the legend and the chapter; the dashboard's
 * real chart is `MoneyFlow` (docs/12 §6.4).
 */
export interface FlowRibbonProps {
  legend: { in: string; out: string; flagged: string }
}

export function FlowRibbon({ legend }: FlowRibbonProps) {
  const ref = useRef<HTMLDivElement>(null)
  const inView = useInViewAttr(ref)

  return (
    <div ref={ref} className="pub-flow" {...inView}>
      <svg viewBox="0 0 400 184" aria-hidden="true" focusable="false">
        <path className="in" pathLength={1} strokeWidth={24} d="M 14 40 C 120 40, 110 88, 198 88" />
        <path className="in" pathLength={1} strokeWidth={12} d="M 14 146 C 120 146, 110 100, 198 100" />
        <path className="out" pathLength={1} strokeWidth={14} d="M 202 82 C 290 82, 280 24, 386 24" />
        <path className="out" pathLength={1} strokeWidth={10} d="M 202 92 C 290 92, 290 74, 386 74" />
        <path className="out" pathLength={1} strokeWidth={7} d="M 202 100 C 290 100, 290 122, 386 122" />
        <path className="flag" pathLength={1} strokeWidth={4} d="M 202 106 C 290 106, 280 164, 386 164" />
        <rect x={194} y={64} width={12} height={56} rx={6} />
      </svg>
      <ul className="pub-flow-legend">
        <li>
          <i aria-hidden="true" />
          {legend.in}
        </li>
        <li>
          <i aria-hidden="true" />
          {legend.out}
        </li>
        <li>
          <i aria-hidden="true" />
          {legend.flagged}
        </li>
      </ul>
    </div>
  )
}
