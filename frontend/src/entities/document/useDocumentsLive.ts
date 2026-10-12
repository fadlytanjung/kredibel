/**
 * Realtime documents collection hook using Firestore onSnapshot (spec 004, AC-004-8).
 *
 * Listens to /orgs/{orgId}/documents in realtime using Firestore's push stream
 * (SSE/Websocket) so document status transitions and page triage reflect immediately
 * without polling the REST API.
 */

import { useEffect, useState } from 'react'
import { collection, onSnapshot, query, orderBy, limit } from 'firebase/firestore'
import { db } from '../../shared/firebase/app'
import type { Document, DocType } from './types'

export interface DocumentLiveFilters {
  type?: DocType
  duplicate?: boolean
}

export interface UseDocumentsLiveResult {
  documents: Document[]
  loading: boolean
  error: Error | null
}

export function useDocumentsLive(
  orgId: string | undefined | null,
  filters?: DocumentLiveFilters,
): UseDocumentsLiveResult {
  const [documents, setDocuments] = useState<Document[]>([])
  const [loading, setLoading] = useState<boolean>(Boolean(orgId))
  const [error, setError] = useState<Error | null>(null)

  useEffect(() => {
    if (!orgId) return

    const colRef = collection(db, 'orgs', orgId, 'documents')
    const q = query(colRef, orderBy('uploadedAt', 'desc'), limit(100))

    const unsubscribe = onSnapshot(
      q,
      (snapshot) => {
        let docs = snapshot.docs.map((docSnap) => ({
          docId: docSnap.id,
          ...(docSnap.data() as Omit<Document, 'docId'>),
        }))
        if (filters?.type) {
          docs = docs.filter((d) => d.docType === filters.type)
        }
        if (filters?.duplicate !== undefined) {
          docs = docs.filter((d) => Boolean(d.heldAsDuplicate) === filters.duplicate)
        }
        setDocuments(docs)
        setLoading(false)
      },
      (err) => {
        setError(err)
        setLoading(false)
      },
    )

    return () => unsubscribe()
  }, [orgId, filters?.type, filters?.duplicate])

  if (!orgId) {
    return { documents: [], loading: false, error: null }
  }

  return { documents, loading, error }
}
