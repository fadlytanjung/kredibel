/**
 * UploadSheet: drop zone, file picker, camera input, per-file progress, and duplicate notice.
 *
 * Normative references:
 * - spec 003 AC-003-1, AC-003-6
 * - docs/11 §6
 * - design/mocks/assets/kit.css .tray, .tray-drop, .tray-list
 */

import { useEffect, useRef, useState, type ChangeEvent, type DragEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { useUploadDocument, type DocType, type Document } from '../../entities/document'
import { ProblemError } from '../../shared/api/client'
import { formatDate } from '../../shared/lib/formatDate'
import { Button, Icon, type IconName } from '../../shared/ui'

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
}

function getUploadItemIcon(item: UploadItem): IconName {
  if (item.document?.status === 'DUPLICATE') return 'copy'
  if (item.status === 'uploading' || item.status === 'queued') return 'refresh'
  if (item.file.name.endsWith('.csv') || item.file.name.endsWith('.xlsx')) return 'table'
  return 'file-text'
}

export function UploadSheet({ onUploaded, docTypeHint, className = '' }: UploadSheetProps) {
  const { t } = useTranslation(['documents', 'errors', 'common'])
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

      {items.length > 0 && (
        <ul className="tray-list" aria-label={t('documents:upload.title')}>
          {items.map((item) => {
            const isDup = item.document?.status === 'DUPLICATE'
            const isUploading = item.status === 'uploading' || item.status === 'queued'
            const isError = item.status === 'error'
            const iconName = getUploadItemIcon(item)

            return (
              <li key={item.id}>
                <span className={`file-ico ${isDup ? 'is-dup' : isUploading ? 'is-busy' : ''}`}>
                  <Icon name={iconName} />
                </span>

                <span className="f">{item.file.name}</span>

                <span className={`m ${isDup ? 'is-dup' : ''}`}>
                  {isUploading && (
                    <>
                      {t('documents:upload.uploading')}
                      <span className="pbar">
                        <i style={{ width: `${item.progress}%` }} /* allow-raw-style: dynamic upload progress */ />
                      </span>
                    </>
                  )}

                  {isError && <span className="text-danger">{item.error}</span>}

                  {isDup && item.document?.duplicate && (
                    <>
                      {t('documents:upload.duplicateNotice', {
                        date: formatDate(item.document.uploadedAt),
                        name: item.document.fileName,
                      })}
                      {' '}
                      <Link to={`/documents/${item.document.duplicate.ofDocId}`}>
                        {t('documents:upload.viewOriginal')}
                      </Link>
                    </>
                  )}

                  {!isUploading && !isError && !isDup && item.document && (
                    <span>
                      {t('documents:status.done')} &middot;{' '}
                      <Link to={`/documents/${item.document.docId}`}>
                        {t('documents:upload.viewOriginal')}
                      </Link>
                    </span>
                  )}
                </span>
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}
