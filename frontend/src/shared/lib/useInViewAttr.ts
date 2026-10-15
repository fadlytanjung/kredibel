import { useEffect, useState, type RefObject } from 'react'
import { usePrefersReducedMotion } from './usePrefersReducedMotion'

export interface InViewOptions {
  /** Stay "in view" once seen (default), or follow the element out again (a contents rail). */
  once?: boolean
  rootMargin?: string
  threshold?: number
}

/**
 * The `data-inview` attribute for a reveal (spec 020, AC-020-12; docs/12 §12): `"false"` until the
 * element enters the viewport, then `"true"`. Where nothing should wait — no IntersectionObserver,
 * or reduced motion — it is `"true"` from the start, so content is never hidden behind a reveal.
 * Spread the result on the element: `<section ref={ref} {...useInViewAttr(ref)}>`.
 */
export function useInViewAttr(
  ref: RefObject<Element | null>,
  { once = true, rootMargin = '0px 0px -12% 0px', threshold = 0.12 }: InViewOptions = {},
) {
  const reduced = usePrefersReducedMotion()
  const observable = typeof window !== 'undefined' && typeof window.IntersectionObserver === 'function'
  const [seen, setSeen] = useState(false)

  useEffect(() => {
    const el = ref.current
    if (!el || reduced || !observable) return
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setSeen(true)
            if (once) observer.disconnect()
          } else if (!once) {
            setSeen(false)
          }
        }
      },
      { rootMargin, threshold },
    )
    observer.observe(el)
    return () => observer.disconnect()
  }, [ref, reduced, observable, once, rootMargin, threshold])

  return { 'data-inview': reduced || !observable || seen ? 'true' : 'false' } as const
}
