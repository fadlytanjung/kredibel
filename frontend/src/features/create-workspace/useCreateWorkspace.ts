/**
 * Create the workspace, then wait until the session carries its claims (AC-013-2 and the spec 013
 * edge case: force a token refresh; if the workspace is still missing, retry once after 2 s).
 */

import { useMutation } from '@tanstack/react-query'
import { useState } from 'react'
import { useAuth } from '../../entities/session'
import { apiClient, ProblemError } from '../../shared/api/client'
import type { WorkspaceCreate } from './schema'

export type CreatePhase = 'idle' | 'creating' | 'finishing' | 'done' | 'notReady'

const RETRY_DELAY_MS = 2000

const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

export function useCreateWorkspace(retryDelayMs = RETRY_DELAY_MS) {
  const { refreshSession } = useAuth()
  const [phase, setPhase] = useState<CreatePhase>('idle')

  const mutation = useMutation({
    mutationFn: async (request: WorkspaceCreate) => {
      setPhase('creating')
      try {
        await apiClient('/api/workspaces', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(request),
        })
      } catch (error) {
        // A double submit or an earlier attempt already created it; the server re-set the claims.
        if (!(error instanceof ProblemError && error.code === 'ALREADY_IN_WORKSPACE')) {
          setPhase('idle')
          throw error
        }
      }

      let me = await refreshSession()
      if (me?.needsWorkspace !== false) {
        setPhase('finishing')
        await wait(retryDelayMs)
        me = await refreshSession()
      }
      setPhase(me?.needsWorkspace === false ? 'done' : 'notReady')
    },
  })

  return { ...mutation, phase }
}
