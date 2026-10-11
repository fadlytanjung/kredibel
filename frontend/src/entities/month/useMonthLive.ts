/**
 * Live month hook using Firestore onSnapshot (spec 004, AC-004-8).
 *
 * Listens to /orgs/{orgId}/months/{month} in realtime so month state,
 * generation, dirty flag, and reconciliation notes update within 2s.
 */

import { useEffect, useState } from 'react'
import { doc, onSnapshot } from 'firebase/firestore'
import { db } from '../../shared/firebase/app'
import type { Month } from './types'

export interface UseMonthLiveResult {
  month: Month | null
  loading: boolean
  error: Error | null
}

export function useMonthLive(
  orgId: string | undefined | null,
  monthKey: string | undefined | null,
): UseMonthLiveResult {
  const [month, setMonth] = useState<Month | null>(null)
  const [loading, setLoading] = useState<boolean>(Boolean(orgId && monthKey))
  const [error, setError] = useState<Error | null>(null)

  useEffect(() => {
    if (!orgId || !monthKey) return

    const docRef = doc(db, 'orgs', orgId, 'months', monthKey)
    const unsubscribe = onSnapshot(
      docRef,
      (snapshot) => {
        if (!snapshot.exists()) {
          setMonth(null)
        } else {
          setMonth({
            month: snapshot.id,
            ...(snapshot.data() as Omit<Month, 'month'>),
          })
        }
        setLoading(false)
      },
      (err) => {
        setError(err)
        setLoading(false)
      },
    )

    return () => {
      unsubscribe()
    }
  }, [orgId, monthKey])

  if (!orgId || !monthKey) {
    return { month: null, loading: false, error: null }
  }

  return { month, loading, error }
}
