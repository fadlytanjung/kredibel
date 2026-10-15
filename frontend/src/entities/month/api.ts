import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '../../shared/api/client'
import type { Month } from './types'

export interface MonthListResponse {
  items: Month[]
}

export function useMonths() {
  return useQuery({
    queryKey: ['months'],
    queryFn: () => apiClient<MonthListResponse>('/api/months'),
  })
}

export function useMonth(month: string | undefined) {
  return useQuery({
    queryKey: ['months', month],
    queryFn: () => apiClient<Month>(`/api/months/${encodeURIComponent(month ?? '')}`),
    enabled: Boolean(month),
  })
}

export function useReconcileMonth() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (month: string) =>
      apiClient<{ runId: string }>(`/api/months/${encodeURIComponent(month)}/reconcile`, {
        method: 'POST',
      }),
    onSuccess: (_, month) => {
      queryClient.invalidateQueries({ queryKey: ['months'] })
      queryClient.invalidateQueries({ queryKey: ['months', month] })
    },
  })
}
