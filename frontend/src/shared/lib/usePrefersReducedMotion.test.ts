import { renderHook, act } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { usePrefersReducedMotion } from './usePrefersReducedMotion'

interface FakeMql {
  matches: boolean
  media: string
  addEventListener: (type: string, cb: () => void) => void
  removeEventListener: (type: string, cb: () => void) => void
}

function stubMatchMedia(initial: boolean) {
  const listeners = new Set<() => void>()
  const mql: FakeMql = {
    matches: initial,
    media: '(prefers-reduced-motion: reduce)',
    addEventListener: (_type, cb) => listeners.add(cb),
    removeEventListener: (_type, cb) => listeners.delete(cb),
  }
  vi.stubGlobal('matchMedia', vi.fn(() => mql))
  return {
    mql,
    flip: () => {
      mql.matches = !mql.matches
      listeners.forEach((cb) => cb())
    },
  }
}

afterEach(() => vi.unstubAllGlobals())

describe('usePrefersReducedMotion', () => {
  it('reports the current preference', () => {
    stubMatchMedia(true)
    const { result } = renderHook(() => usePrefersReducedMotion())
    expect(result.current).toBe(true)
  })

  it('follows a change in the preference', () => {
    const { flip } = stubMatchMedia(false)
    const { result } = renderHook(() => usePrefersReducedMotion())
    expect(result.current).toBe(false)
    act(() => flip())
    expect(result.current).toBe(true)
  })
})
