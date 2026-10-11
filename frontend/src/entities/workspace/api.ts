import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../../shared/api/client'
import type { Workspace } from './shellProps'

export function useWorkspace(enabled: boolean) {
  return useQuery({
    queryKey: ['workspace'],
    queryFn: () => apiClient<Workspace>('/api/workspace'),
    enabled,
  })
}
