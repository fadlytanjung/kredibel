import { vi } from 'vitest'

/**
 * Test helper for the scene hooks (spec 020, T020-20): `matchMedia` answering per query, so a test
 * can say "fine pointer, no reduced motion" or the opposite. jsdom has no `matchMedia` of its own.
 */
export function stubMedia(answers: Record<string, boolean>) {
  vi.stubGlobal(
    'matchMedia',
    vi.fn((media: string) => ({
      matches: answers[media] ?? false,
      media,
      addEventListener: () => {},
      removeEventListener: () => {},
    })),
  )
}

export const REDUCED = '(prefers-reduced-motion: reduce)'
export const FINE_POINTER = '(pointer: fine)'
