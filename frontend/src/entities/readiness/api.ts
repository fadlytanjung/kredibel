import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../../shared/api/client'
import type { components } from '../../shared/api/schema'

export type Readiness = components['schemas']['Readiness']
export type ReadinessCheck = components['schemas']['ReadinessCheck']

/** Spec 025, AC-025-1…3: whether the books are ready to show a lender, and why. */
export function useReadiness() {
  return useQuery({
    queryKey: ['readiness'],
    queryFn: () => apiClient<Readiness>('/api/readiness'),
  })
}
