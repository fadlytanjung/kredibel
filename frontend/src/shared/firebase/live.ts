/**
 * Realtime subscriptions load the Firestore SDK on first use (AC-010-11): the first paint does
 * not pay for it, and a page that never listens never downloads it.
 */

import type { Firestore } from 'firebase/firestore'
import { liveDb } from './app'

export type FirestoreSdk = typeof import('firebase/firestore')

/**
 * Loads the SDK and the database, then subscribes. The returned function unsubscribes, or cancels
 * a subscription that is still loading; a load failure reaches `onError`.
 */
export function subscribeLive(
  subscribe: (sdk: FirestoreSdk, db: Firestore) => () => void,
  onError: (error: Error) => void,
): () => void {
  let cancelled = false
  let unsubscribe: (() => void) | null = null
  void Promise.all([import('firebase/firestore'), liveDb()]).then(
    ([sdk, db]) => {
      if (!cancelled) unsubscribe = subscribe(sdk, db)
    },
    (error: unknown) => {
      if (!cancelled) onError(error instanceof Error ? error : new Error(String(error)))
    },
  )
  return () => {
    cancelled = true
    unsubscribe?.()
  }
}
