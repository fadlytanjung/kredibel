import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../../shared/api/client'
import type { components } from '../../shared/api/schema'

export type ExpectationComparison = components['schemas']['ExpectationComparison']
export type ExpectationSide = components['schemas']['ExpectationSide']
export type MonthExpectation = components['schemas']['MonthExpectation']

/** Spec 024, AC-024-5: each expected month against its reconciled money in and out. */
export function useExpectations(enabled = true) {
  return useQuery({
    queryKey: ['expectations'],
    queryFn: () => apiClient<ExpectationComparison>('/api/expectations'),
    enabled,
  })
}
