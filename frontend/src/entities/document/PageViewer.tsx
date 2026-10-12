/**
 * The page viewer: one rendered page at a time with its pages and zoom, and the lamp on the value
 * being looked at (docs/11 §6.3, §6.6; mock design/mocks/document.html).
 */

import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useSizeClass } from '../../shared/lib/useSizeClass'
import { Badge, Icon } from '../../shared/ui'
import { type PageBox, PageImage } from './PageImage'

const ZOOMS = [50, 75, 100, 125, 150, 200]

interface PageViewerProps {
  docId: string
  fileName: string
  pageCount: number
  page: number
  onPage: (page: number) => void
  highlight?: PageBox
  witness?: 'TEXT_LAYER' | 'OCR' | 'NONE'
}

export function PageViewer({ docId, fileName, pageCount, page, onPage, highlight, witness }: PageViewerProps) {
  const { t } = useTranslation('documents')
  // A phone opens the page zoomed in, scrolled to the value (docs/11 §6.6).
  const { isCompact } = useSizeClass()
  const [zoom, setZoom] = useState(isCompact ? 200 : 100)
  const step = (by: number) =>
    setZoom((z) => ZOOMS[Math.min(ZOOMS.length - 1, Math.max(0, ZOOMS.indexOf(z) + by))] ?? 100)

  return (
    <section className="viewer" aria-label={t('detail.viewer.label')}>
      <div className="viewer-bar">
        <span className="file">
          <Icon name="file-text" size="sm" />
          {fileName}
        </span>
        {witness && witness !== 'NONE' && (
          <Badge variant="outline">{witness === 'TEXT_LAYER' ? t('detail.digital') : t('detail.scanned')}</Badge>
        )}
        <span className="pages" role="group" aria-label={t('detail.viewer.pages')}>
          <button type="button" aria-label={t('detail.viewer.previous')} disabled={page <= 1} onClick={() => onPage(page - 1)}>
            <Icon name="chevron-left" size="sm" />
          </button>
          <span>{t('detail.viewer.pageOf', { page, total: pageCount })}</span>
          <button
            type="button"
            aria-label={t('detail.viewer.next')}
            disabled={page >= pageCount}
            onClick={() => onPage(page + 1)}
          >
            <Icon name="chevron-right" size="sm" />
          </button>
        </span>
        <span className="zoom" role="group" aria-label={t('detail.viewer.zoom')}>
          <button type="button" aria-label={t('detail.viewer.zoomOut')} disabled={zoom === ZOOMS[0]} onClick={() => step(-1)}>
            <Icon name="zoom-out" size="sm" />
          </button>
          <span>{t('detail.viewer.zoomLevel', { zoom })}</span>
          <button
            type="button"
            aria-label={t('detail.viewer.zoomIn')}
            disabled={zoom === ZOOMS[ZOOMS.length - 1]}
            onClick={() => step(1)}
          >
            <Icon name="zoom-in" size="sm" />
          </button>
        </span>
      </div>
      <div className="doc-window is-image" data-page-frame>
        <div className="page-zoom" style={{ width: `${zoom}%` }} /* allow-raw-style: the zoom level */>
          <PageImage docId={docId} pageNo={page} variant="full" alt={t('detail.page', { page })} highlight={highlight} />
        </div>
      </div>
      <p className="muted small">{highlight ? t('detail.viewer.lit') : t('detail.viewer.hint')}</p>
    </section>
  )
}
