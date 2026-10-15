import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../../shared/api/client'
import type { components } from '../../shared/api/schema'

export type Run = components['schemas']['Run']
export type RunPage = components['schemas']['RunPage']
export type RunStage = components['schemas']['RunStage']
export type AgentEvent = components['schemas']['AgentEvent']
export type AgentEventPage = components['schemas']['AgentEventPage']

export interface RunFilters {
  kind?: string
  status?: string
  target?: string
  limit?: number
}

/** Runs, newest first (docs/10; spec 017). */
export function useRuns(filters: RunFilters = {}, enabled = true) {
  const params = new URLSearchParams()
  if (filters.kind) params.set('kind', filters.kind)
  if (filters.status) params.set('status', filters.status)
  if (filters.target) params.set('target', filters.target)
  if (filters.limit) params.set('limit', String(filters.limit))
  const qs = params.toString()
  return useQuery({
    queryKey: ['runs', filters],
    queryFn: () => apiClient<RunPage>(`/api/runs${qs ? `?${qs}` : ''}`),
    enabled,
  })
}

export function useRun(runId: string | undefined) {
  return useQuery({
    queryKey: ['runs', 'one', runId],
    queryFn: () => apiClient<Run>(`/api/runs/${encodeURIComponent(runId ?? '')}`),
    enabled: Boolean(runId),
  })
}

/** The run's events from its stages, joined to the labels it produced (AC-017-6). */
export function useRunEvents(runId: string | undefined, enabled = true) {
  return useQuery({
    queryKey: ['runs', 'events', runId],
    queryFn: () => apiClient<AgentEventPage>(`/api/runs/${encodeURIComponent(runId ?? '')}/events`),
    enabled: enabled && Boolean(runId),
  })
}
