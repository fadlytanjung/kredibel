/** A rendered page, fetched with the token (docs/11 §6.3). */

import { useAuthedObjectUrl } from './media'

interface PageImageProps {
  docId: string
  pageNo: number
  variant: 'thumb' | 'full'
  alt: string
  className?: string
}

export function PageImage({ docId, pageNo, variant, alt, className }: PageImageProps) {
  const { url, isError } = useAuthedObjectUrl(`/api/documents/${docId}/pages/${pageNo}?variant=${variant}`)
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
  return <img src={url} alt={alt} className={className} />
}

