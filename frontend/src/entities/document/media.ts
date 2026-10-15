/**
 * Page images and the original file need the ID token, which an `<img src>` or a plain link cannot
 * send (every page came back 401). They are fetched through the API client and shown from object
 * URLs (docs/11 §6.3).
 */

import { useQuery } from '@tanstack/react-query'
import { apiBlob } from '../../shared/api/client'

const objectUrlCache = new Map<string, string>()

function getCachedObjectUrl(path: string, blob: Blob): string {
  let url = objectUrlCache.get(path)
  if (!url) {
    url = URL.createObjectURL(blob)
    objectUrlCache.set(path, url)
  }
  return url
}

export function useAuthedObjectUrl(path: string | null) {
  const query = useQuery({
    queryKey: ['blob', path],
    queryFn: () => apiBlob(path as string),
    enabled: path !== null,
    staleTime: Infinity, // a rendered page never changes
  })
  const url = query.data && path ? getCachedObjectUrl(path, query.data) : undefined
  return { url, isError: query.isError }
}

/** Fetch the original with the token and hand it to the browser as a download. */
export async function downloadOriginal(docId: string, fileName: string): Promise<void> {
  const blob = await apiBlob(`/api/documents/${docId}/file`)
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = fileName
  document.body.appendChild(link)
  link.click()
  link.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
