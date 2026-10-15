import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '../../shared/api/client'
import type { Counterparty, CounterpartyPage, CounterpartyRole, Suggestion, SuggestionDecision } from './types'

export interface CounterpartyFilters {
  role?: CounterpartyRole
  q?: string
  limit?: number
}

export function useCounterparties(filters: CounterpartyFilters = {}, enabled = true) {
  const params = new URLSearchParams()
  if (filters.role) params.set('role', filters.role)
  if (filters.q) params.set('q', filters.q)
  params.set('limit', String(filters.limit ?? 500))
  return useQuery({
    queryKey: ['counterparties', filters],
    queryFn: () => apiClient<CounterpartyPage>(`/api/counterparties?${params.toString()}`),
    enabled,
  })
}

export function useCounterparty(counterpartyId: string | undefined) {
  return useQuery({
    queryKey: ['counterparty', counterpartyId],
    queryFn: () => apiClient<Counterparty>(`/api/counterparties/${counterpartyId}`),
    enabled: Boolean(counterpartyId),
  })
}

export function useSuggestions(status?: Suggestion['status'], enabled = true) {
  const query = status ? `?status=${status}` : ''
  return useQuery({
    queryKey: ['suggestions', status ?? 'all'],
    queryFn: () => apiClient<{ items: Suggestion[] }>(`/api/suggestions${query}`),
    enabled,
  })
}

/** A person's decision on a suggestion (AC-014-5): the profile and the lists follow. */
export function useDecideSuggestion() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ suggestionId, decision }: { suggestionId: string; decision: SuggestionDecision }) =>
      apiClient<Suggestion>(`/api/suggestions/${suggestionId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ decision }),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['suggestions'] })
      void queryClient.invalidateQueries({ queryKey: ['workspace'] })
      void queryClient.invalidateQueries({ queryKey: ['bank-accounts'] })
    },
  })
}
