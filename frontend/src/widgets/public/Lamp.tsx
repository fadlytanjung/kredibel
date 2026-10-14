import { useRef, type ReactNode } from 'react'
import { useInViewAttr } from '../../shared/lib/useInViewAttr'
import { usePointerTilt } from '../../shared/lib/usePointerTilt'

/**
 * An ink section lit by the violet evidence lamp (spec 018, AC-018-12; docs/12 §12). On a fine
 * pointer the lamp follows the cursor, and every depth scene inside tilts with it (the section
 * writes `--rx`/`--ry`/`--lx`/`--ly`, which its descendants inherit). `reveal` adds `data-inview`
 * for scenes that open as the section arrives.
 */
export interface LampProps {
  children: ReactNode
  className?: string
  labelledBy?: string
  reveal?: boolean
}

export function Lamp({ children, className, labelledBy, reveal = false }: LampProps) {
  const ref = useRef<HTMLElement>(null)
  usePointerTilt(ref)
  const inView = useInViewAttr(ref)

  return (
    <section
      ref={ref}
      className={className ? `pub-ink ${className}` : 'pub-ink'}
      aria-labelledby={labelledBy}
      {...(reveal ? inView : {})}
    >
      {children}
    </section>
  )
}
