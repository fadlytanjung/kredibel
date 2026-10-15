import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '../../shared/api/client'
import type { components } from '../../shared/api/schema'

export type ProfitLoss = components['schemas']['ProfitLoss']
export type Classification = components['schemas']['AccountClassification']
export type Accounts = components['schemas']['ProfitLossAccounts']

export function useProfitLoss(period: string) {
  return useQuery({ queryKey: ['profit-loss', period], queryFn: () =>
    apiClient<ProfitLoss>(`/api/profit-loss?period=${encodeURIComponent(period)}`) })
}
export function useProfitLossAccounts() {
  return useQuery({ queryKey: ['profit-loss-accounts'], queryFn: () =>
    apiClient<Accounts>('/api/profit-loss/accounts') })
}
export function useConfirmClassification() {
  const client = useQueryClient()
  return useMutation({ mutationFn: (body: Classification) =>
    apiClient<Classification>('/api/profit-loss/accounts', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }),
  onSuccess: async () => {
    await Promise.all([
      client.invalidateQueries({ queryKey: ['profit-loss'] }),
      client.invalidateQueries({ queryKey: ['profit-loss-accounts'] }),
    ])
  } })
}
