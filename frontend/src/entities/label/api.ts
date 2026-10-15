import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '../../shared/api/client'
import type { components } from '../../shared/api/schema'

export type Label = components['schemas']['Label']
export type LabelPage = components['schemas']['LabelPage']
export type LabelSummary = components['schemas']['LabelSummary']
export type LabelDecision = components['schemas']['LabelDecision']
export type LabelTask = components['schemas']['LabelTask']
export type LabelStatus = components['schemas']['LabelStatus']

export interface LabelFilters {
  task?: string
  status?: string
  needsCheck?: boolean
  docId?: string
  month?: string
  sort?: 'confidence' | 'newest'
  limit?: number
}

function query(filters: LabelFilters): string {
  const params = new URLSearchParams()
  if (filters.task) params.set('task', filters.task)
  if (filters.status) params.set('status', filters.status)
  if (filters.needsCheck !== undefined) params.set('needsCheck', String(filters.needsCheck))
  if (filters.docId) params.set('docId', filters.docId)
  if (filters.month) params.set('month', filters.month)
  if (filters.sort) params.set('sort', filters.sort)
  if (filters.limit) params.set('limit', String(filters.limit))
  const qs = params.toString()
  return qs ? `?${qs}` : ''
}

/** Labels, lowest confidence first, with the summary of what people checked (docs/10 §2.10). */
export function useLabels(filters: LabelFilters = {}, enabled = true) {
  return useQuery({
    queryKey: ['labels', filters],
    queryFn: () => apiClient<LabelPage>(`/api/labels${query(filters)}`),
    enabled,
  })
}

export function useLabel(labelId: string | undefined) {
  return useQuery({
    queryKey: ['labels', 'one', labelId],
    queryFn: () => apiClient<Label>(`/api/labels/${encodeURIComponent(labelId ?? '')}`),
    enabled: Boolean(labelId),
  })
}

function invalidate(queryClient: ReturnType<typeof useQueryClient>) {
  for (const key of ['labels', 'bank-lines', 'months', 'month', 'runs', 'documents']) {
    void queryClient.invalidateQueries({ queryKey: [key] })
  }
}

/** A person confirms or corrects one label (AC-016-6, AC-016-7). */
export function useDecideLabel() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ labelId, decision }: { labelId: string; decision: LabelDecision }) =>
      apiClient<Label>(`/api/labels/${encodeURIComponent(labelId)}/decision`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(decision),
      }),
    onSuccess: () => invalidate(queryClient),
  })
}

/** Confirm up to 200 labels as the AI proposed them. */
export function useBulkConfirm() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (labelIds: string[]) =>
      apiClient<{ updated: number }>('/api/labels/bulk-confirm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ labelIds }),
      }),
    onSuccess: () => invalidate(queryClient),
  })
}
