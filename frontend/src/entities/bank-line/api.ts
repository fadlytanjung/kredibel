import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../../shared/api/client'
import type { components } from '../../shared/api/schema'

export type BankLine = components['schemas']['BankLine']
export type BankLinePage = components['schemas']['BankLinePage']
export type ValueReading = components['schemas']['ValueReading']
export type BBox = components['schemas']['BBox']

/** One statement's lines, with how each value was read (docs/10 §2.4). */
export function useBankLines(docId: string | undefined) {
  return useQuery({
    queryKey: ['bank-lines', { docId }],
    queryFn: () => apiClient<BankLinePage>(`/api/bank-lines?docId=${encodeURIComponent(docId ?? '')}`),
    enabled: Boolean(docId),
  })
}

/** Every bank line of the workspace, newest statements included (the all-months views, T007-10c). */
export function useAllBankLines(enabled = true) {
  return useQuery({
    queryKey: ['bank-lines', { all: true }],
    queryFn: () => apiClient<BankLinePage>('/api/bank-lines?limit=1000'),
    enabled,
  })
}

/** All bank lines of a given month (docs/10 §2.4). */
export function useMonthBankLines(month: string | undefined) {
  return useQuery({
    queryKey: ['bank-lines', { month }],
    queryFn: () => apiClient<BankLinePage>(`/api/bank-lines?month=${encodeURIComponent(month ?? '')}`),
    enabled: Boolean(month),
  })
}

