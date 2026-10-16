/**
 * The upload tray's rows (spec 003, AC-003-1, AC-003-6; docs/11 §6.3 and its upload state diagram):
 * files sending from this tab, then the workspace's uploads of the last day and any upload still
 * waiting for a person (a held copy, a ledger's columns, a file that needs input or failed), newest
 * first. Each row names its state and, when there is one, the person's next step.
 */

import type { Document } from '../../entities/document'
import type { ReviewItem } from '../../entities/review'

export type TrayState = 'uploading' | 'error' | 'copy' | 'held' | 'reading' | 'columns' | 'needsInput' | 'failed' | 'done'

export interface TrayRow {
  key: string
  fileName: string
  state: TrayState
  docId?: string
  progress?: number // 0 to 100, for uploading and reading
  page?: number // reading: the page being read
  pages?: number
  original?: { docId: string; fileName: string; uploadedAt: string }
  reasonCode?: string // the duplicate code of a held copy
  reviewItemId?: string
  detail?: string // the server's sentence for needs input and failed
  docType?: string
  rows?: number
}

export interface LocalUpload {
  id: string
  fileName: string
  status: 'queued' | 'uploading' | 'done' | 'error'
  progress: number
  docId?: string
  error?: string
}

export const TRAY_MAX_ROWS = 6
const DAY_MS = 24 * 60 * 60 * 1000
const BUSY = ['UPLOADED', 'SCREENING', 'READING', 'CHECKING']

function needsPerson(doc: Document): boolean {
  if (doc.heldAsDuplicate) return true
  if (doc.docType === 'LEDGER_EXPORT' && doc.ledgerMeta?.mappingStatus === 'PROPOSED') return true
  return doc.status === 'NEEDS_INPUT' || doc.status === 'FAILED'
}

export function rowOf(doc: Document, byId: Map<string, Document>, items: ReviewItem[]): TrayRow {
  const base = { key: doc.docId, fileName: doc.fileName, docId: doc.docId, docType: doc.docType }
  const original = doc.duplicate?.ofDocId ? byId.get(doc.duplicate.ofDocId) : undefined
  // The original may not be loaded (the tray on its own): it is still linked, by its ID.
  const originalRef = original
    ? { docId: original.docId, fileName: original.fileName, uploadedAt: original.uploadedAt }
    : doc.duplicate?.ofDocId
      ? { docId: doc.duplicate.ofDocId, fileName: '', uploadedAt: '' }
      : undefined
  if (doc.status === 'DUPLICATE') return { ...base, state: 'copy', original: originalRef }
  if (doc.heldAsDuplicate) {
    return { ...base, state: 'held', original: originalRef, reasonCode: doc.duplicate?.code, reviewItemId: doc.duplicate?.reviewItemId }
  }
  if (doc.docType === 'LEDGER_EXPORT' && doc.ledgerMeta?.mappingStatus === 'PROPOSED') {
    const item = items.find((i) => i.kind === 'CONFIRM_LEDGER_MAPPING' && i.docId === doc.docId)
    return { ...base, state: 'columns', reviewItemId: item?.itemId }
  }
  if (BUSY.includes(doc.status)) {
    const pages = doc.pageCount || doc.pages?.length || 0
    const done = (doc.pages ?? []).filter((p) => p.status === 'DONE' || p.status === 'BLANK').length
    const progress = pages ? Math.round(((Math.min(done, pages - 1) + 0.5) / pages) * 100) : undefined
    return { ...base, state: 'reading', page: pages ? Math.min(done + 1, pages) : undefined, pages, progress }
  }
  if (doc.status === 'NEEDS_INPUT') {
    const item = items.find((i) => i.docId === doc.docId)
    return { ...base, state: 'needsInput', detail: doc.statusDetail, reviewItemId: item?.itemId }
  }
  if (doc.status === 'FAILED' || doc.status === 'QUARANTINED') return { ...base, state: 'failed', detail: doc.statusDetail }
  return { ...base, state: 'done', rows: doc.ledgerMeta?.rowsImported ?? doc.ledgerMeta?.rows ?? undefined }
}

export function trayRows(docs: Document[], local: LocalUpload[], items: ReviewItem[], now: Date = new Date()): TrayRow[] {
  const byId = new Map(docs.map((d) => [d.docId, d]))
  const rows: TrayRow[] = []
  const shown = new Set<string>()
  for (const upload of local) {
    if (upload.status === 'queued' || upload.status === 'uploading') {
      rows.push({ key: upload.id, fileName: upload.fileName, state: 'uploading', progress: upload.progress })
    } else if (upload.status === 'error') {
      rows.push({ key: upload.id, fileName: upload.fileName, state: 'error', detail: upload.error })
    } else if (upload.docId) {
      const doc = byId.get(upload.docId)
      if (doc) rows.push(rowOf(doc, byId, items))
      shown.add(upload.docId)
    }
  }
  const recent = docs
    .filter((d) => !shown.has(d.docId))
    .filter((d) => needsPerson(d) || now.getTime() - Date.parse(d.uploadedAt ?? '') < DAY_MS)
    .sort((a, b) => Date.parse(b.uploadedAt ?? '') - Date.parse(a.uploadedAt ?? ''))
  for (const doc of recent) rows.push(rowOf(doc, byId, items))
  return rows.slice(0, TRAY_MAX_ROWS)
}
