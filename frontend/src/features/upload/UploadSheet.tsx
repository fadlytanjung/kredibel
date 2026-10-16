/**
 * UploadSheet: drop zone, file picker, camera input, per-file progress, and duplicate notice.
 *
 * Normative references:
 * - spec 003 AC-003-1, AC-003-6
 * - docs/11 §6
 * - design/mocks/assets/kit.css .tray, .tray-drop, .tray-list
 */

import { useEffect, useRef, useState, type ChangeEvent, type DragEvent } from 'react'
import { Trans, useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { useUploadDocument, type DocType, type Document } from '../../entities/document'
import { useReviewItems } from '../../entities/review'
import { ProblemError } from '../../shared/api/client'
import { formatDate } from '../../shared/lib/formatDate'
import { Button, Icon, type IconName } from '../../shared/ui'
import { type TrayRow, type TrayState, trayRows } from './trayRows'

export interface UploadItem {
  id: string
  file: File
  status: 'queued' | 'uploading' | 'done' | 'error'
  progress: number
  document?: Document
  error?: string
}

export interface UploadSheetProps {
  onUploaded?: (doc: Document) => void
  docTypeHint?: DocType
  className?: string
  /** The workspace's documents, live: the tray follows each upload and shows what waits for a person. */
  documents?: Document[]
}

const ICON: Record<TrayState, IconName> = {
  uploading: 'refresh',
  reading: 'refresh',
  copy: 'copy',
  held: 'copy',
  columns: 'table',
  needsInput: 'triangle-alert',
  failed: 'triangle-alert',
  error: 'triangle-alert',
  done: 'file-text',
}
const ICON_TONE: Partial<Record<TrayState, string>> = { uploading: 'is-busy', reading: 'is-busy', copy: 'is-dup', held: 'is-held' }

function rowIcon(row: TrayRow): IconName {
  if (row.state === 'done' && row.docType === 'LEDGER_EXPORT') return 'table'
  if (row.state === 'done' && row.docType === 'RECEIPT') return 'receipt'
  return ICON[row.state]
}

export function UploadSheet({ onUploaded, docTypeHint, className = '', documents = [] }: UploadSheetProps) {
  const { t } = useTranslation(['documents', 'errors', 'common'])
  // Only a ledger waiting for its columns or a file that needs input is found through the queue;
  // a held copy names its review item itself.
  const { data: review } = useReviewItems(
    documents.some((d) => d.status === 'NEEDS_INPUT' || (d.docType === 'LEDGER_EXPORT' && d.ledgerMeta?.mappingStatus === 'PROPOSED')),
  )
  const uploadMutation = useUploadDocument()
  const [items, setItems] = useState<UploadItem[]>([])
  const [isDragging, setIsDragging] = useState(false)

  const fileInputRef = useRef<HTMLInputElement>(null)
  const cameraInputRef = useRef<HTMLInputElement>(null)

  // Uploads start from this effect, never from a state updater: React may call an updater twice
  // (StrictMode does), and each call would send the file again. `started` makes a start happen
  // once per item even if the effect itself runs twice.
  const started = useRef(new Set<string>())

  const upload = async (item: UploadItem) => {
    try {
      const doc = await uploadMutation.mutateAsync({
        file: item.file,
        docTypeHint: docTypeHint ? docTypeHint : undefined,
      })
      setItems((prev) =>
        prev.map((i) =>
          i.id === item.id ? { ...i, status: 'done' as const, progress: 100, document: doc } : i,
        ),
      )
      onUploaded?.(doc)
    } catch (err) {
      let errorMsg = t('errors:fallback')
      if (err instanceof ProblemError) {
        errorMsg = t(`errors:${err.code}`, { defaultValue: err.message })
      } else if (err instanceof Error) {
        errorMsg = err.message
      }
      setItems((prev) =>
        prev.map((i) =>
          i.id === item.id ? { ...i, status: 'error' as const, progress: 100, error: errorMsg } : i,
        ),
      )
    }
  }

  useEffect(() => {
    // At most 3 uploads at a time (AC-003-1).
    const active = items.filter((i) => i.status === 'uploading').length
    const toStart = items
      .filter((i) => i.status === 'queued' && !started.current.has(i.id))
      .slice(0, Math.max(0, 3 - active))
    if (toStart.length === 0) return
    for (const item of toStart) started.current.add(item.id)
    setItems((prev) =>
      prev.map((i) =>
        toStart.some((s) => s.id === i.id) ? { ...i, status: 'uploading' as const, progress: 30 } : i,
      ),
    )
    for (const item of toStart) void upload(item)
    // `upload` reads the latest props through its closure; the queue only reacts to items.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [items])

  const enqueueFiles = (files: FileList | File[]) => {
    const newItems: UploadItem[] = Array.from(files).map((f) => ({
      id: `${f.name}-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
      file: f,
      status: 'queued',
      progress: 0,
    }))

    setItems((prev) => [...newItems, ...prev])
  }

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      enqueueFiles(e.target.files)
      e.target.value = ''
    }
  }

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setIsDragging(true)
  }

  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setIsDragging(false)
  }

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setIsDragging(false)
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      enqueueFiles(e.dataTransfer.files)
    }
  }

  // Files sending from this tab, then the workspace's uploads of the last day and anything waiting.
  const now = new Date()
  const rows = trayRows(
    documents.length ? documents : items.flatMap((i) => (i.document ? [i.document] : [])),
    items.map((i) => ({ id: i.id, fileName: i.file.name, status: i.status, progress: i.progress, docId: i.document?.docId, error: i.error })),
    review?.items ?? [],
    now,
  )
  const original = (row: TrayRow) =>
    row.original ? (
      <Link to={`/documents/${encodeURIComponent(row.original.docId)}`}>{row.original.fileName || t('documents:upload.anEarlierFile')}</Link>
    ) : (
      <span>{t('documents:upload.anEarlierFile')}</span>
    )
  const message = (row: TrayRow) => {
    switch (row.state) {
      case 'uploading':
        return (
          <>
            {t('documents:upload.uploading')}
            <span className="pbar">
              <i style={{ width: `${row.progress ?? 0}%` }} /* allow-raw-style: dynamic upload progress */ />
            </span>
          </>
        )
      case 'reading':
        return row.page && row.pages ? (
          <>
            {t('documents:upload.readingPage', { page: row.page, total: row.pages })}
            <span className="pbar">
              <i style={{ width: `${row.progress ?? 0}%` }} /* allow-raw-style: the share of pages read */ />
            </span>
          </>
        ) : (
          t('documents:upload.readingFile')
        )
      case 'copy':
        return (
          <Trans
            t={t}
            i18nKey={row.original?.uploadedAt ? 'documents:upload.copyNotice' : 'documents:upload.copyNoticePlain'}
            values={{ date: row.original?.uploadedAt ? formatDate(row.original.uploadedAt, { year: undefined }) : '', name: row.original?.fileName || t('documents:upload.anEarlierFile') }}
            components={{ original: original(row) }}
          />
        )
      case 'held':
        return (
          <Trans
            t={t}
            i18nKey={row.reasonCode && t(`documents:upload.heldReasons.${row.reasonCode}`, { defaultValue: '' }) ? 'documents:upload.heldNotice' : 'documents:upload.heldNoticePlain'}
            values={{ name: row.original?.fileName || t('documents:upload.anEarlierFile'), reason: row.reasonCode ? t(`documents:upload.heldReasons.${row.reasonCode}`, { defaultValue: '' }) : '' }}
            components={{ original: original(row) }}
          />
        )
      case 'columns':
        return t('documents:upload.columnsNotice')
      case 'needsInput':
        return row.detail || t('documents:status.needsInput')
      case 'failed':
        return <span className="text-danger">{row.detail || t('documents:upload.failed')}</span>
      case 'error':
        return <span className="text-danger">{row.detail || t('errors:fallback')}</span>
      default:
        return row.rows ? t('documents:upload.rowsImported', { count: row.rows }) : t('documents:upload.read', { type: t(`documents:detail.docType.${row.docType}`, { defaultValue: '' }) || t('documents:status.done') })
    }
  }
  const action = (row: TrayRow) => {
    const to = row.reviewItemId ? `/review/${encodeURIComponent(row.reviewItemId)}` : '/review'
    if (row.state === 'held')
      return (
        <span className="act">
          <Link className="button button-secondary button-sm" to={to}>
            {t('documents:upload.decide')}
          </Link>
        </span>
      )
    if (row.state === 'columns')
      return (
        <span className="act">
          <Link className="button button-primary button-sm" to={to}>
            {t('documents:upload.checkColumns')}
          </Link>
        </span>
      )
    if (row.state === 'needsInput')
      return (
        <span className="act">
          <Link className="button button-secondary button-sm" to={to}>
            {t('documents:upload.review')}
          </Link>
        </span>
      )
    if (row.state === 'done' && row.docId)
      return (
        <span className="act">
          <Link className="button button-quiet button-sm" to={`/documents/${encodeURIComponent(row.docId)}`}>
            {t('documents:upload.open')}
          </Link>
        </span>
      )
    return null
  }

  return (
    <section
      className={`tray ${isDragging ? 'is-dragging' : ''} ${className}`.trim()}
      aria-labelledby="tray-h"
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept=".pdf,.png,.jpg,.jpeg,.csv,.xlsx,application/pdf,image/png,image/jpeg,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        className="hidden"
        onChange={handleFileChange}
        data-testid="file-input"
      />
      <input
        ref={cameraInputRef}
        type="file"
        accept="image/*"
        capture="environment"
        className="hidden"
        onChange={handleFileChange}
        data-testid="camera-input"
      />

      <div className="tray-drop">
        <span className="ico">
          <Icon name="upload" />
        </span>
        <p>
          <strong id="tray-h">{t('documents:upload.title')}</strong>
          {t('documents:upload.description')}
        </p>

        <Button
          variant="primary"
          onClick={() => fileInputRef.current?.click()}
          type="button"
        >
          <Icon name="plus" size="sm" />
          {t('documents:upload.chooseFiles')}
        </Button>

        <Button
          variant="secondary"
          className="only-compact"
          onClick={() => cameraInputRef.current?.click()}
          type="button"
        >
          <Icon name="camera" size="sm" />
          {t('documents:upload.takePhoto')}
        </Button>
      </div>

      {rows.length > 0 && (
        <ul className="tray-list" aria-label={t('documents:upload.justUploaded')}>
          {rows.map((row) => (
            <li key={row.key}>
              <span className={`file-ico ${ICON_TONE[row.state] ?? ''}`.trim()}>
                <Icon name={rowIcon(row)} />
              </span>
              <span className="f">{row.fileName}</span>
              <span className={`m${row.state === 'copy' ? ' is-dup' : ''}`}>{message(row)}</span>
              {action(row)}
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
