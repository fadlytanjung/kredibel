/** A rendered page, fetched with the token (docs/11 §6.3). */

import { useEffect, useRef, useState } from 'react'
import { useAuthedObjectUrl } from './media'

/** A box on the page, normalized 0..1 from the top left (contracts BBox). */
export interface PageBox {
  x0: number
  y0: number
  x1: number
  y1: number
}

interface PageImageProps {
  docId: string
  pageNo: number
  variant: 'thumb' | 'full'
  alt: string
  className?: string
  /** The lamp: the box of the value being looked at (docs/11 §6.3). */
  highlight?: PageBox
}

export function PageImage({ docId, pageNo, variant, alt, className, highlight }: PageImageProps) {
  const { url, isError } = useAuthedObjectUrl(`/api/documents/${docId}/pages/${pageNo}?variant=${variant}`)
  const lamp = useRef<HTMLSpanElement>(null)
  // The lamp can only be measured once the image has its size, so the image is never remounted
  // when a value is lit, and a new page waits for its load.
  const [loaded, setLoaded] = useState<string>()
  useEffect(() => {
    const box = lamp.current
    if (!url || !highlight || !box || loaded !== url) return
    // Centre the lamp in the viewer's scrolling window, then bring the window into view: one
    // smooth scrollIntoView does not move a nested scroller and the page together.
    const frame = box.closest<HTMLElement>('[data-page-frame]')
    if (frame) {
      const f = frame.getBoundingClientRect()
      const b = box.getBoundingClientRect()
      frame.scrollTo?.({
        left: frame.scrollLeft + b.left - f.left - (f.width - b.width) / 2,
        top: frame.scrollTop + b.top - f.top - (f.height - b.height) / 2,
      })
    }
    ;(frame ?? box).scrollIntoView?.({ block: 'nearest', behavior: 'smooth' })
  }, [url, highlight, loaded])
  if (isError) {
    return (
      <span role="img" aria-label={alt} className="muted small block p-4 text-center">
        {alt}
      </span>
    )
  }
  if (!url) {
    return <span role="img" aria-label={alt} aria-busy="true" className={`block bg-sunken ${className ?? ''}`} />
  }
  const pad = 0.004
  const box = highlight && {
    left: `${(highlight.x0 - pad) * 100}%`,
    top: `${(highlight.y0 - pad) * 100}%`,
    width: `${(highlight.x1 - highlight.x0 + 2 * pad) * 100}%`,
    height: `${(highlight.y1 - highlight.y0 + 2 * pad) * 100}%`,
  }
  return (
    <span className="page-figure">
      <img src={url} alt={alt} className={className} onLoad={() => setLoaded(url)} />
      {box && (
        <span
          ref={lamp}
          className="lamp on-page"
          data-testid="page-lamp"
          style={box} /* allow-raw-style: the box comes from the value's normalized coordinates */
        />
      )}
    </span>
  )
}
