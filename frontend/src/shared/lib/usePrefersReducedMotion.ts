import { useMediaQuery } from './useMediaQuery'

/**
 * True when the visitor asked for reduced motion (`prefers-reduced-motion: reduce`).
 * The hero animation renders in its settled state instead of playing (spec 020, AC-020-2), and every
 * public scene settles (AC-020-12).
 */
export function usePrefersReducedMotion(): boolean {
  return useMediaQuery('(prefers-reduced-motion: reduce)')
}
