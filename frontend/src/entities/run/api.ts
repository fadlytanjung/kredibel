import { useQueries, useQuery } from '@tanstack/react-query'
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

const RUN_KINDS = ['DOCUMENT', 'MONTH', 'ASSISTANT'] as const

/** The latest runs as the API lists them, then the latest of each kind not already among them: once a
 * workspace has a few hundred documents the first hundred runs are all month runs, and the Document
 * chip would count none. */
export function useRunsByKind(limit: number, enabled = true) {
  const results = useQueries({
    queries: [undefined, ...RUN_KINDS].map((kind) => ({
      queryKey: ['runs', { kind, limit }],
      queryFn: () => apiClient<RunPage>(`/api/runs?${kind ? `kind=${kind}&` : ''}limit=${limit}`),
      enabled,
    })),
  })
  const seen = new Set<string>()
  const items: Run[] = []
  for (const result of results) {
    for (const run of result.data?.items ?? []) {
      if (seen.has(run.runId)) continue
      seen.add(run.runId)
      items.push(run)
    }
  }
  return {
    data: results[0].data ? { items } : undefined,
    isLoading: results[0].isLoading,
    isError: results[0].isError,
    refetch: () => Promise.all(results.map((r) => r.refetch())),
  }
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
