import { useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '../../shared/api/client'
import type { components } from '../../shared/api/schema'

export type Decision = components['schemas']['Decision']
export type DecisionCreate = components['schemas']['DecisionCreate']
export type DecisionKind = components['schemas']['DecisionKind']

export function useCreateDecision() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: DecisionCreate) =>
      apiClient<Decision>('/api/decisions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['decisions'] })
      void queryClient.invalidateQueries({ queryKey: ['bank-lines'] })
      void queryClient.invalidateQueries({ queryKey: ['months'] })
      void queryClient.invalidateQueries({ queryKey: ['month'] })
      void queryClient.invalidateQueries({ queryKey: ['review-items'] })
    },
  })
}

export function useWithdrawDecision() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (decisionId: string) =>
      apiClient<void>(`/api/decisions/${encodeURIComponent(decisionId)}`, {
        method: 'DELETE',
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['decisions'] })
      void queryClient.invalidateQueries({ queryKey: ['bank-lines'] })
      void queryClient.invalidateQueries({ queryKey: ['months'] })
      void queryClient.invalidateQueries({ queryKey: ['month'] })
      void queryClient.invalidateQueries({ queryKey: ['review-items'] })
    },
  })
}
