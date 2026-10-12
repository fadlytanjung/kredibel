import { act, renderHook } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { useDocumentsLive } from './useDocumentsLive'

type DocumentsSnapshotCallback = (snapshot: {
  docs: Array<{
    id: string
    data: () => Record<string, unknown>
  }>
}) => void

let snapshotCallback: DocumentsSnapshotCallback | null = null
const unsubscribeMock = vi.fn()

vi.mock('firebase/firestore', () => ({
  collection: vi.fn((_db, ...parts: string[]) => parts.join('/')),
  query: vi.fn((col) => col),
  orderBy: vi.fn(),
  limit: vi.fn(),
  onSnapshot: vi.fn((_ref, onNext) => {
    snapshotCallback = onNext
    return unsubscribeMock
  }),
}))

vi.mock('../../shared/firebase/app', () => ({
  db: {},
}))

describe('useDocumentsLive (push-based realtime documents)', () => {
  beforeEach(() => {
    snapshotCallback = null
    vi.clearAllMocks()
  })

  it('subscribes to documents collection and updates state on snapshot', () => {
    const { result } = renderHook(() => useDocumentsLive('org_test'))

    expect(result.current.loading).toBe(true)
    expect(result.current.documents).toEqual([])

    act(() => {
      snapshotCallback?.({
        docs: [
          {
            id: 'doc_1',
            data: () => ({
              fileName: 'statement.pdf',
              status: 'DONE',
              docType: 'BANK_STATEMENT',
              pageCount: 3,
            }),
          },
          {
            id: 'doc_2',
            data: () => ({
              fileName: 'invoice.pdf',
              status: 'READING',
              docType: 'SALES_INVOICE',
              pageCount: 1,
            }),
          },
        ],
      })
    })

    expect(result.current.loading).toBe(false)
    expect(result.current.documents.length).toBe(2)
    expect(result.current.documents[0].docId).toBe('doc_1')
    expect(result.current.documents[0].status).toBe('DONE')
    expect(result.current.documents[1].docId).toBe('doc_2')
    expect(result.current.documents[1].status).toBe('READING')
  })

  it('applies client-side filters on live updates', () => {
    const { result } = renderHook(() =>
      useDocumentsLive('org_test', { type: 'BANK_STATEMENT' }),
    )

    act(() => {
      snapshotCallback?.({
        docs: [
          {
            id: 'doc_1',
            data: () => ({
              fileName: 'statement.pdf',
              docType: 'BANK_STATEMENT',
              status: 'DONE',
            }),
          },
          {
            id: 'doc_2',
            data: () => ({
              fileName: 'invoice.pdf',
              docType: 'SALES_INVOICE',
              status: 'DONE',
            }),
          },
        ],
      })
    })

    expect(result.current.documents.length).toBe(1)
    expect(result.current.documents[0].docId).toBe('doc_1')
  })

  it('cleans up subscription on unmount', () => {
    const { unmount } = renderHook(() => useDocumentsLive('org_test'))
    unmount()
    expect(unsubscribeMock).toHaveBeenCalled()
  })

  it('returns empty list without subscribing when orgId is missing', () => {
    const { result } = renderHook(() => useDocumentsLive(null))
    expect(result.current.loading).toBe(false)
    expect(result.current.documents).toEqual([])
  })
})
