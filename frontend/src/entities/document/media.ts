/**
 * Page images and the original file need the ID token, which an `<img src>` or a plain link cannot
 * send (every page came back 401). They are fetched through the API client and shown from object
 * URLs (docs/11 §6.3).
 */

import { useQuery } from '@tanstack/react-query'
import { useEffect, useMemo } from 'react'
import { apiBlob } from '../../shared/api/client'

export function useAuthedObjectUrl(path: string | null) {
  const query = useQuery({
    queryKey: ['blob', path],
    queryFn: () => apiBlob(path as string),
    enabled: path !== null,
    staleTime: Infinity, // a rendered page never changes
  })
  const url = useMemo(() => (query.data ? URL.createObjectURL(query.data) : undefined), [query.data])
  useEffect(() => () => (url ? URL.revokeObjectURL(url) : undefined), [url])
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
