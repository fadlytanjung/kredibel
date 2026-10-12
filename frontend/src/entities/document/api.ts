import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '../../shared/api/client'
import type { DocType, Document, DocumentPage } from './types'

export interface DocumentFilters {
  type?: DocType
  month?: string
  status?: string
  duplicate?: boolean
  risk?: string
  limit?: number
  cursor?: string
}

export function useDocuments(filters?: DocumentFilters, enabled = true) {
  const params = new URLSearchParams()
  if (filters?.type) params.set('type', filters.type)
  if (filters?.month) params.set('month', filters.month)
  if (filters?.status) params.set('status', filters.status)
  if (filters?.duplicate !== undefined) params.set('duplicate', String(filters.duplicate))
  if (filters?.risk) params.set('risk', filters.risk)
  if (filters?.limit) params.set('limit', String(filters.limit))
  if (filters?.cursor) params.set('cursor', filters.cursor)

  const queryStr = params.toString()
  const path = queryStr ? `/api/documents?${queryStr}` : '/api/documents'

  return useQuery({
    queryKey: ['documents', filters],
    queryFn: () => apiClient<DocumentPage>(path),
    enabled,
  })
}

export function useDocument(docId: string | undefined, enabled = true) {
  return useQuery({
    queryKey: ['document', docId],
    queryFn: () => apiClient<Document>(`/api/documents/${docId}`),
    enabled: Boolean(docId && enabled),
  })
}

export interface UploadPayload {
  file: File
  docTypeHint?: DocType
}

export function useUploadDocument() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: async ({ file, docTypeHint }: UploadPayload) => {
      const formData = new FormData()
      formData.append('file', file)
      if (docTypeHint) {
        formData.append('docTypeHint', docTypeHint)
      }
      return apiClient<Document>('/api/documents', {
        method: 'POST',
        body: formData,
      })
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['documents'] })
      void queryClient.invalidateQueries({ queryKey: ['workspace'] })
    },
  })
}

export function useDeleteDocument() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (docId: string) =>
      apiClient<void>(`/api/documents/${docId}`, {
        method: 'DELETE',
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['documents'] })
      void queryClient.invalidateQueries({ queryKey: ['workspace'] })
    },
  })
}
