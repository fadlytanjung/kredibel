/**
 * Open the demo company (spec 021, AC-021-1): the server copies the demo template into a new
 * workspace for this person; then the session is refreshed for its claims, as after creating one.
 */

import { useMutation } from '@tanstack/react-query'
import { useState } from 'react'
import { useAuth } from '../../entities/session'
import { apiClient, ProblemError } from '../../shared/api/client'
import type { CreatePhase } from './useCreateWorkspace'

const RETRY_DELAY_MS = 2000
const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

export function useOpenDemo(retryDelayMs = RETRY_DELAY_MS) {
  const { refreshSession } = useAuth()
  const [phase, setPhase] = useState<CreatePhase>('idle')

  const mutation = useMutation({
    mutationFn: async () => {
      setPhase('creating')
      try {
        await apiClient('/api/workspaces/demo', { method: 'POST' })
      } catch (error) {
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
