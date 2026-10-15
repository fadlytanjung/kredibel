import { useMotionValueEvent, useSpring } from 'motion/react'
import { useEffect, type RefObject } from 'react'
import { useMediaQuery } from './useMediaQuery'
import { usePrefersReducedMotion } from './usePrefersReducedMotion'

const SPRING = { stiffness: 140, damping: 18, mass: 0.6 }

/**
 * Pointer-driven depth on a scene (spec 020, AC-020-12; docs/12 §12). On a fine pointer it writes:
 * `--rx` / `--ry` — the tilt, −1…1, eased by a spring (CSS turns it into degrees);
 * `--lx` / `--ly` — where the pointer is, as a percentage of the element (the violet lamp);
 * `data-pointer="on"` while the pointer is over the element.
 * Touch and reduced motion get nothing, and the scene stays upright.
 */
export function usePointerTilt(ref: RefObject<HTMLElement | null>) {
  const reduced = usePrefersReducedMotion()
  const fine = useMediaQuery('(pointer: fine)')
  const tiltX = useSpring(0, SPRING)
  const tiltY = useSpring(0, SPRING)

  useMotionValueEvent(tiltX, 'change', (value) => ref.current?.style.setProperty('--rx', value.toFixed(4)))
  useMotionValueEvent(tiltY, 'change', (value) => ref.current?.style.setProperty('--ry', value.toFixed(4)))

  useEffect(() => {
    const el = ref.current
    if (!el || reduced || !fine) return

    const onMove = (event: PointerEvent) => {
      const box = el.getBoundingClientRect()
      if (!box.width || !box.height) return
      const x = Math.min(1, Math.max(0, (event.clientX - box.left) / box.width))
      const y = Math.min(1, Math.max(0, (event.clientY - box.top) / box.height))
      tiltX.set((0.5 - y) * 2)
      tiltY.set((x - 0.5) * 2)
      el.style.setProperty('--lx', `${(x * 100).toFixed(2)}%`)
      el.style.setProperty('--ly', `${(y * 100).toFixed(2)}%`)
      el.dataset.pointer = 'on'
    }
    const onLeave = () => {
      tiltX.set(0)
      tiltY.set(0)
      delete el.dataset.pointer
    }

    el.addEventListener('pointermove', onMove)
    el.addEventListener('pointerleave', onLeave)
    return () => {
      el.removeEventListener('pointermove', onMove)
      el.removeEventListener('pointerleave', onLeave)
      onLeave()
    }
  }, [ref, reduced, fine, tiltX, tiltY])
}
