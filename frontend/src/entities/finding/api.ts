import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '../../shared/api/client'
import type { components } from '../../shared/api/schema'

export type Finding = components['schemas']['Finding']
export type FindingPage = components['schemas']['FindingPage']
export type FindingUpdate = components['schemas']['FindingUpdate']

export interface FindingsFilter {
  month?: string
  docId?: string
  status?: string
  severity?: string
  code?: string
}

/** List findings with optional filters (docs/10 §2.5). */
export function useFindings(filters: FindingsFilter = {}) {
  const query = new URLSearchParams()
  if (filters.month) query.set('month', filters.month)
  if (filters.docId) query.set('docId', filters.docId)
  if (filters.status) query.set('status', filters.status)
  if (filters.severity) query.set('severity', filters.severity)
  if (filters.code) query.set('code', filters.code)
  const qs = query.toString()

  return useQuery({
    queryKey: ['findings', filters],
    queryFn: () => apiClient<FindingPage>(qs ? `/api/findings?${qs}` : '/api/findings'),
  })
}

/** Single finding by ID (AC-008-8, AC-008-9). */
export function useFinding(findingId: string | undefined) {
  return useQuery({
    queryKey: ['finding', findingId],
    queryFn: () => apiClient<Finding>(`/api/findings/${findingId}`),
    enabled: Boolean(findingId),
  })
}

/** Acknowledge or dismiss finding with reason (AC-008-9). */
export function useUpdateFinding() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ findingId, update }: { findingId: string; update: FindingUpdate }) =>
      apiClient<Finding>(`/api/findings/${findingId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(update),
      }),
    onSuccess: (data) => {
      queryClient.setQueryData(['finding', data.findingId], data)
      void queryClient.invalidateQueries({ queryKey: ['findings'] })
      void queryClient.invalidateQueries({ queryKey: ['months'] })
      if (data.month) {
        void queryClient.invalidateQueries({ queryKey: ['month', data.month] })
      }
    },
  })
}

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
