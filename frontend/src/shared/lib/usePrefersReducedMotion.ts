import { useMediaQuery } from './useMediaQuery'

/**
 * True when the visitor asked for reduced motion (`prefers-reduced-motion: reduce`).
 * The hero animation renders in its settled state instead of playing (spec 018, AC-018-2), and every
 * public scene settles (AC-018-12).
 */
export function usePrefersReducedMotion(): boolean {
  return useMediaQuery('(prefers-reduced-motion: reduce)')
}
