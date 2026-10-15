import { act, renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useMonthLive } from './useMonthLive'

type SnapshotCallback = (snapshot: {
  id: string
  exists: () => boolean
  data: () => Record<string, unknown>
}) => void

let snapshotCallback: SnapshotCallback | null = null
const unsubscribeMock = vi.fn()

vi.mock('firebase/firestore', () => ({
  doc: vi.fn((_db, ...parts: string[]) => parts.join('/')),
  onSnapshot: vi.fn((_ref, onNext) => {
    snapshotCallback = onNext
    return unsubscribeMock
  }),
}))

vi.mock('../../shared/firebase/app', () => ({
  liveDb: () => Promise.resolve({}),
}))

describe('useMonthLive (AC-004-8)', () => {
  beforeEach(() => {
    snapshotCallback = null
    vi.clearAllMocks()
  })

  it('subscribes to month and updates state on snapshot', async () => {
    const { result } = renderHook(() => useMonthLive('org_test', '2026-03'))
    await waitFor(() => expect(snapshotCallback).not.toBeNull())

    expect(result.current.loading).toBe(true)
    expect(result.current.month).toBeNull()

    act(() => {
      snapshotCallback?.({
        id: '2026-03',
        exists: () => true,
        data: () => ({
          state: 'RECONCILING',
          generation: 2,
          dirty: false,
          figures: {},
        }),
      })
    })

    expect(result.current.loading).toBe(false)
    expect(result.current.month?.month).toBe('2026-03')
    expect(result.current.month?.state).toBe('RECONCILING')
    expect(result.current.month?.generation).toBe(2)
  })

  it('cleans up subscription on unmount', async () => {
    const { unmount } = renderHook(() => useMonthLive('org_test', '2026-03'))
    await waitFor(() => expect(snapshotCallback).not.toBeNull())
    unmount()
    expect(unsubscribeMock).toHaveBeenCalled()
  })

  it('handles null orgId or monthKey without subscribing', () => {
    const { result } = renderHook(() => useMonthLive(null, null))
    expect(result.current.loading).toBe(false)
    expect(result.current.month).toBeNull()
  })
})
