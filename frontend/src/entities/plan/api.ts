import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../../shared/api/client'
import type { components } from '../../shared/api/schema'

export type PlanCatalog = components['schemas']['PlanCatalog']
export type Plan = components['schemas']['Plan']

export function usePlans() {
  return useQuery({
    queryKey: ['plans'],
    queryFn: () => apiClient<PlanCatalog>('/api/plans'),
  })
}

/** The plan a new workspace starts on: the first AVAILABLE plan (contracts/plans.v1.yaml). */
export function trialPlan(catalog: PlanCatalog | undefined): Plan | undefined {
  return catalog?.plans.find((plan) => plan.status === 'AVAILABLE')
}
