import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../../shared/api/client'
import type { components } from '../../shared/api/schema'

export type Transaction = components['schemas']['Transaction']
export interface TransactionList {
  month: string
  items: Transaction[]
}

/** Spec 024, AC-024-6: every bank line of a month with its classes, subledger and records. */
export function useTransactions(month: string | undefined) {
  return useQuery({
    queryKey: ['transactions', month],
    queryFn: () => apiClient<TransactionList>(`/api/transactions?month=${encodeURIComponent(month ?? '')}`),
    enabled: Boolean(month),
  })
}
