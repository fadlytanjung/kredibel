import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '../../shared/api/client'
import type { components } from '../../shared/api/schema'

export type Match = components['schemas']['Match']
export type MatchPage = components['schemas']['MatchPage']
export type MatchCreate = components['schemas']['MatchCreate']

export function useMatches(month: string | undefined) {
  return useQuery({
    queryKey: ['matches', { month }],
    queryFn: () => apiClient<MatchPage>(`/api/matches?month=${encodeURIComponent(month ?? '')}`),
    enabled: Boolean(month),
  })
}

export function useCreateMatch() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: MatchCreate) =>
      apiClient<Match>('/api/matches', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['matches'] })
      queryClient.invalidateQueries({ queryKey: ['bank-lines'] })
      queryClient.invalidateQueries({ queryKey: ['months'] })
    },
  })
}

export function useUnmatch() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (matchId: string) =>
      apiClient<void>(`/api/matches/${encodeURIComponent(matchId)}`, {
        method: 'DELETE',
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['matches'] })
      queryClient.invalidateQueries({ queryKey: ['bank-lines'] })
      queryClient.invalidateQueries({ queryKey: ['months'] })
    },
  })
}
