/**
 * Live document hook using Firestore onSnapshot (spec 004, AC-004-8).
 *
 * Listens to /orgs/{orgId}/documents/{docId} in realtime so the SPA
 * reflects status, triage, and page reading progress without polling.
 */

import { useEffect, useState } from 'react'
import { subscribeLive } from '../../shared/firebase/live'
import type { Document } from './types'

export interface UseDocumentLiveResult {
  document: Document | null
  loading: boolean
  error: Error | null
}

export function useDocumentLive(
  orgId: string | undefined | null,
  docId: string | undefined | null,
): UseDocumentLiveResult {
  const [document, setDocument] = useState<Document | null>(null)
  const [loading, setLoading] = useState<boolean>(Boolean(orgId && docId))
  const [error, setError] = useState<Error | null>(null)

  useEffect(() => {
    if (!orgId || !docId) return

    return subscribeLive(
      ({ doc, onSnapshot }, db) =>
        onSnapshot(
          doc(db, 'orgs', orgId, 'documents', docId),
          (snapshot) => {
            if (!snapshot.exists()) {
              setDocument(null)
            } else {
              setDocument({
                docId: snapshot.id,
                ...(snapshot.data() as Omit<Document, 'docId'>),
              })
            }
            setLoading(false)
          },
          (err) => {
            setError(err)
            setLoading(false)
          },
        ),
      (err) => {
        setError(err)
        setLoading(false)
      },
    )
  }, [orgId, docId])

  if (!orgId || !docId) {
    return { document: null, loading: false, error: null }
  }

  return { document, loading, error }
}
