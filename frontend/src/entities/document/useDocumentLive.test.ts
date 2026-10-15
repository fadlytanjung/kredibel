import { act, renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useDocumentLive } from './useDocumentLive'

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

describe('useDocumentLive (AC-004-8)', () => {
  beforeEach(() => {
    snapshotCallback = null
    vi.clearAllMocks()
  })

  it('subscribes to document and updates state on snapshot', async () => {
    const { result } = renderHook(() => useDocumentLive('org_test', 'doc_123'))
    await waitFor(() => expect(snapshotCallback).not.toBeNull())

    expect(result.current.loading).toBe(true)
    expect(result.current.document).toBeNull()

    act(() => {
      snapshotCallback?.({
        id: 'doc_123',
        exists: () => true,
        data: () => ({
          fileName: 'statement.pdf',
          status: 'READING',
          pageCount: 18,
          pages: [{ pageNo: 1, status: 'DONE' }, { pageNo: 2, status: 'DONE' }],
        }),
      })
    })

    expect(result.current.loading).toBe(false)
    expect(result.current.document?.docId).toBe('doc_123')
    expect(result.current.document?.status).toBe('READING')
    expect(result.current.document?.pages?.length).toBe(2)
  })

  it('cleans up subscription on unmount', async () => {
    const { unmount } = renderHook(() => useDocumentLive('org_test', 'doc_123'))
    await waitFor(() => expect(snapshotCallback).not.toBeNull())
    unmount()
    expect(unsubscribeMock).toHaveBeenCalled()
  })

  it('handles null orgId or docId without subscribing', () => {
    const { result } = renderHook(() => useDocumentLive(null, null))
    expect(result.current.loading).toBe(false)
    expect(result.current.document).toBeNull()
  })
})
