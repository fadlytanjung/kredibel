import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../../shared/api/client'
import type { components } from '../../shared/api/schema'

export type Dashboard = components['schemas']['Dashboard']
export type Kpi = components['schemas']['Kpi']
export type MonthSummary = components['schemas']['MonthSummary']
export type Alert = components['schemas']['Alert']
export type FlowNode = components['schemas']['FlowNode']
export type FlowLink = components['schemas']['FlowLink']
export type MoneyFlow = components['schemas']['MoneyFlow']
export type CashFlow = components['schemas']['CashFlow']
export type FlowView = 'STATEMENT' | 'COUNTERPARTIES'
export type Framework = 'IFRS' | 'US_GAAP'
type BankLinePage = components['schemas']['BankLinePage']

function query(params: Record<string, string | undefined>): string {
  const q = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) if (value) q.set(key, value)
  return q.toString()
}

/** A period: a month, quarter, year, range, recent or all (contracts Period, docs/10 §2.7). */
export function useDashboard(period: string) {
  return useQuery({
    queryKey: ['dashboard', { period }],
    queryFn: () => apiClient<Dashboard>(`/api/dashboard?period=${encodeURIComponent(period)}`),
  })
}

/** Nodes and links of where the money went in a period (AC-010-5, docs/08 §5.1). */
export function useMoneyFlow(period: string, view: FlowView, framework?: Framework) {
  return useQuery({
    queryKey: ['money-flow', { period, view, framework }],
    queryFn: () => apiClient<MoneyFlow>(`/api/money-flow?${query({ period, view, framework })}`),
  })
}

/** Months in and out, activities and the opening-to-closing check (AC-010-13, AC-010-14). */
export function useCashFlow(period: string, framework?: Framework) {
  return useQuery({
    queryKey: ['cash-flow', { period, framework }],
    queryFn: () => apiClient<CashFlow>(`/api/cash-flow?${query({ period, framework })}`),
  })
}

/** The bank lines behind one band or node of the money flow (AC-010-6). */
export function useFlowLines(flow: string | undefined, period: string, view: FlowView, framework?: Framework) {
  return useQuery({
    queryKey: ['flow-lines', { flow, period, view, framework }],
    queryFn: () => apiClient<BankLinePage>(`/api/bank-lines?${query({ flow, period, view, framework })}`),
    enabled: Boolean(flow),
  })
}
