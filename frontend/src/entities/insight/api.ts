import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../../shared/api/client'
import type { components } from '../../shared/api/schema'

export type Dashboard = components['schemas']['Dashboard']
export type Kpi = components['schemas']['Kpi']
export type MonthSummary = components['schemas']['MonthSummary']
export type Alert = components['schemas']['Alert']
export type FlowNode = components['schemas']['FlowNode']

/** A period: a month, quarter, year, range, recent or all (contracts Period, docs/10 §2.7). */
export function useDashboard(period: string) {
  return useQuery({
    queryKey: ['dashboard', { period }],
    queryFn: () => apiClient<Dashboard>(`/api/dashboard?period=${encodeURIComponent(period)}`),
  })
}
