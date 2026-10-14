import { useRef, type ReactNode } from 'react'
import { useInViewAttr } from '../../shared/lib/useInViewAttr'

/**
 * A block whose children rise into place, one after another, as it scrolls into view (spec 018,
 * AC-018-12; docs/12 §12). The stagger is in `kit.css` (`.pub-reveal`), so no child needs a style.
 * Without IntersectionObserver or under reduced motion everything is simply shown.
 */
export interface RevealProps {
  children: ReactNode
  className?: string
}

export function Reveal({ children, className }: RevealProps) {
  const ref = useRef<HTMLDivElement>(null)
  const inView = useInViewAttr(ref)

  return (
    <div ref={ref} className={className ? `pub-reveal ${className}` : 'pub-reveal'} {...inView}>
      {children}
    </div>
  )
}
