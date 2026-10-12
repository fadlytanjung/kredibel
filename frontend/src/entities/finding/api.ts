import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../../shared/api/client'
import type { components } from '../../shared/api/schema'

export type Finding = components['schemas']['Finding']
export type FindingPage = components['schemas']['FindingPage']

/** A document's findings, most severe first (docs/10 §2.5). */
export function useDocumentFindings(docId: string | undefined) {
  return useQuery({
    queryKey: ['findings', { docId }],
    queryFn: () => apiClient<FindingPage>(`/api/findings?docId=${encodeURIComponent(docId ?? '')}`),
    enabled: Boolean(docId),
  })
}

export interface EvidenceFocus {
  key: string
  page: number
  bbox: { x0: number; y0: number; x1: number; y1: number }
}

/** The first piece of evidence with a box: where the finding is shown on the page. */
export function evidenceFocus(f: Finding): EvidenceFocus | undefined {
  const ev = f.evidence.find((e) => e.bbox && e.page)
  return ev?.bbox && ev.page ? { key: f.findingId, page: ev.page, bbox: ev.bbox } : undefined
}
