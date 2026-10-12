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
