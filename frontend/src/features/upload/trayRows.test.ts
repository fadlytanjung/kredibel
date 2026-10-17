import { describe, expect, it } from 'vitest'
import fixture from '../../../../contracts/design/fixtures/documents.json'
import type { Document } from '../../entities/document'
import type { ReviewItem } from '../../entities/review'
import { TRAY_MAX_ROWS, trayRows } from './trayRows'

const DOCS = fixture.items as unknown as Document[]
const ITEMS = fixture.reviewItems as unknown as ReviewItem[]
const NOW = new Date(fixture.now)

describe('the upload tray (spec 003, AC-003-1, AC-003-6)', () => {
  it('shows the last day and anything waiting for a person, newest first, with its next step', () => {
    const rows = trayRows(DOCS, [], ITEMS, NOW)
    expect(rows.map((r) => [r.fileName, r.state])).toEqual([
      ['ACB_Feb_2026 (1).pdf', 'copy'],
      ['Receipt 0617 (2).jpg', 'held'],
      ['ACB_Jun_2026.pdf', 'reading'],
      ['ledger-2026-H1.csv', 'columns'],
    ])
    expect(rows[0].original).toEqual({ docId: 'doc_feb', fileName: 'ACB_Feb_2026.pdf', uploadedAt: '2026-07-02T08:30:00Z' })
    expect(rows[1]).toMatchObject({ reasonCode: 'D05_RECEIPT_DUPLICATE', reviewItemId: 'itm_rcp_0617_2' })
    expect(rows[2]).toMatchObject({ page: 2, pages: 3, progress: 50 })
    expect(rows[3].reviewItemId).toBe('itm_ledger_h1')
  })

  it('lists only what was uploaded since the workspace began: a demo copy\'s files were not (spec 024)', () => {
    // The demo company is copied with its documents' upload times; in a copy made within a day
    // of them they are not this workspace's uploads. Anything waiting for a person still shows.
    expect(trayRows(DOCS, [], ITEMS, NOW, NOW).map((r) => r.state)).toEqual(['held', 'columns'])
  })

  it('keeps a held copy or a ledger waiting for its columns after the day; read files leave', () => {
    const later = new Date('2026-07-12T09:30:00Z')
    expect(trayRows(DOCS, [], ITEMS, later).map((r) => r.state)).toEqual(['held', 'columns'])
  })

  it('puts files sending from this tab first, then follows them by their document', () => {
    const rows = trayRows(
      DOCS,
      [
        { id: 'u1', fileName: 'INV-SCR-2026-06-0025.pdf', status: 'uploading', progress: 30 },
        { id: 'u2', fileName: 'big.pdf', status: 'error', progress: 100, error: 'Too many pages' },
        { id: 'u3', fileName: 'ACB_Jun_2026.pdf', status: 'done', progress: 100, docId: 'doc_jun' },
      ],
      ITEMS,
      NOW,
    )
    expect(rows.map((r) => r.state)).toEqual(['uploading', 'error', 'reading', 'copy', 'held', 'columns'])
    expect(rows.filter((r) => r.docId === 'doc_jun')).toHaveLength(1)
    expect(rows.length).toBeLessThanOrEqual(TRAY_MAX_ROWS)
  })
})
