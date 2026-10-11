import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '../../shared/api/client'
import type { components } from '../../shared/api/schema'

export type BankAccount = components['schemas']['BankAccount']
export type BankAccountCreate = components['schemas']['BankAccountCreate']
export type BankAccountUpdate = components['schemas']['BankAccountUpdate']

const KEY = ['bank-accounts']
const json = (method: string, body: unknown): RequestInit => ({
  method,
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
})

export function useBankAccounts() {
  return useQuery({
    queryKey: KEY,
    queryFn: async () => (await apiClient<{ items: BankAccount[] }>('/api/bank-accounts')).items,
  })
}

export function useAddBankAccount() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (body: BankAccountCreate) =>
      apiClient<BankAccount>('/api/bank-accounts', json('POST', body)),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: KEY }),
  })
}

export function useUpdateBankAccount() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ accountId, patch }: { accountId: string; patch: BankAccountUpdate }) =>
      apiClient<BankAccount>(`/api/bank-accounts/${accountId}`, json('PATCH', patch)),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: KEY }),
  })
}

export function useDeleteBankAccount() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (accountId: string) =>
      apiClient<void>(`/api/bank-accounts/${accountId}`, { method: 'DELETE' }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: KEY }),
  })
}
