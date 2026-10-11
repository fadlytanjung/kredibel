import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '../../shared/api/client'
import type { components } from '../../shared/api/schema'
import type { Workspace } from './shellProps'

export type WorkspaceUpdate = components['schemas']['WorkspaceUpdate']

export function useWorkspace(enabled = true) {
  return useQuery({
    queryKey: ['workspace'],
    queryFn: () => apiClient<Workspace>('/api/workspace'),
    enabled,
  })
}

export function useUpdateWorkspace() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (patch: WorkspaceUpdate) =>
      apiClient<Workspace>('/api/workspace', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(patch),
      }),
    onSuccess: (workspace) => queryClient.setQueryData(['workspace'], workspace),
  })
}
