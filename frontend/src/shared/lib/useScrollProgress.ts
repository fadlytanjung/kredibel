import { useMotionValueEvent, useScroll } from 'motion/react'
import { useState, type RefObject } from 'react'
import { usePrefersReducedMotion } from './usePrefersReducedMotion'

type ScrollOffset = NonNullable<NonNullable<Parameters<typeof useScroll>[0]>['offset']>

export interface ScrollProgressOptions {
  /** How the element's travel maps to 0…1 (motion's `offset`); default: from entering to leaving. */
  offset?: ScrollOffset
  /** Split the progress into this many chapters and return the current one (0-based). */
  chapters?: number
  /** Measure the whole page instead of the element (the header's reading-progress rule). */
  page?: boolean
}

/**
 * Scroll progress as the CSS custom property `--p` (0…1) on the element (spec 020, AC-020-12;
 * docs/12 §12). Every visual that follows the scroll reads `--p` in `kit.css`; nothing here sets a
 * style value of its own. Under reduced motion nothing is written and the chapter stays 0, and the
 * CSS shows every scene settled.
 */
export function useScrollProgress(
  ref: RefObject<HTMLElement | null>,
  { offset = ['start end', 'end start'], chapters = 0, page = false }: ScrollProgressOptions = {},
): number {
  const reduced = usePrefersReducedMotion()
  const { scrollYProgress } = useScroll(page ? {} : { target: ref, offset })
  const [chapter, setChapter] = useState(0)

  useMotionValueEvent(scrollYProgress, 'change', (value) => {
    const el = ref.current
    if (!el || reduced) return
    el.style.setProperty('--p', value.toFixed(4))
    if (chapters > 0) setChapter(Math.min(chapters - 1, Math.max(0, Math.floor(value * chapters))))
  })

  return chapter
}
