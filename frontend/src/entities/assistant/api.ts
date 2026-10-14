import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '../../shared/api/client'

export interface Thread {
  threadId: string
  title?: string | null
  scope: string
  createdAt?: string | null
  lastMessageAt?: string | null
}

export interface ThreadListResponse {
  items: Thread[]
  nextCursor?: string | null
}

export interface CitationRef {
  ref: string
  label: string
}

export interface GroundingInfo {
  verdict: 'AGREED' | 'TEMPLATE' | 'REJECTED'
  citations: string[]
}

export interface AnswerPart {
  type: 'text' | 'table' | 'chart'
  text?: string | null
  columns?: string[] | null
  rows?: string[][] | null
  chart?: 'MONEY_FLOW' | 'MONTHLY_IN_OUT' | 'CATEGORY_BREAKDOWN' | null
  query?: Record<string, unknown> | null
}

export interface MessageAnswer {
  parts: AnswerPart[]
  citations: CitationRef[]
  grounding?: GroundingInfo | null
  toolsUsed: string[]
}

export interface AssistantMessage {
  messageId: string
  role: 'user' | 'assistant'
  question?: string | null
  answer?: MessageAnswer | null
  createdAt: string
}

export interface MessageListResponse {
  items: AssistantMessage[]
}

export interface MatchAiSuggestion {
  recommendedDocId: string | null
  confidence: number
  reason: string
  missingDocumentAdvice: string
}

/** List conversation threads in the workspace. */
export function useThreads(limit = 20, cursor?: string | null) {
  return useQuery({
    queryKey: ['assistant-threads', { limit, cursor }],
    queryFn: () => {
      const params = new URLSearchParams()
      params.set('limit', String(limit))
      if (cursor) params.set('cursor', cursor)
      return apiClient<ThreadListResponse>(`/api/assistant/threads?${params.toString()}`)
    },
  })
}

/** Infinite paginated conversation threads in the workspace. */
export function useInfiniteThreads(limit = 10) {
  return useInfiniteQuery({
    queryKey: ['assistant-threads-infinite', { limit }],
    queryFn: ({ pageParam }) => {
      const params = new URLSearchParams()
      params.set('limit', String(limit))
      if (pageParam) params.set('cursor', pageParam)
      return apiClient<ThreadListResponse>(`/api/assistant/threads?${params.toString()}`)
    },
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (lastPage) => lastPage.nextCursor ?? undefined,
  })
}

/** Create a new conversation thread. */
export function useCreateThread() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ title, scope = 'WORKSPACE' }: { title?: string; scope?: string }) =>
      apiClient<Thread>('/api/assistant/threads', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, scope }),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['assistant-threads'] })
      void queryClient.invalidateQueries({ queryKey: ['assistant-threads-infinite'] })
    },
  })
}

/** List messages in a thread. */
export function useMessages(threadId: string | undefined) {
  return useQuery({
    queryKey: ['assistant-messages', threadId],
    queryFn: () => apiClient<MessageListResponse>(`/api/assistant/threads/${threadId}/messages`),
    enabled: Boolean(threadId),
  })
}

/** Ask a question in a thread. */
export function useAskQuestion(threadId: string | undefined) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ question }: { question: string }) =>
      apiClient<AssistantMessage>(`/api/assistant/threads/${threadId}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question }),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['assistant-messages', threadId] })
      void queryClient.invalidateQueries({ queryKey: ['assistant-threads'] })
    },
  })
}

/** Get AI reconciliation suggestion for a bank transaction line. */
export function useBankLineAiSuggestion(txId: string | undefined, enabled = true) {
  return useQuery({
    queryKey: ['bank-line-ai-suggestion', txId],
    queryFn: async () => {
      const res = await apiClient<MatchAiSuggestion>(`/api/bank-lines/${txId}/ai-suggestion`)
      return res ?? null
    },
    enabled: Boolean(txId) && enabled,
  })
}

export interface AssistantMemory {
  memoryId: string
  fact: string
  updatedAt?: string | null
}

export interface MemoryListResponse {
  items: AssistantMemory[]
}

/** List preferences remembered by the assistant. */
export function useMemories() {
  return useQuery({
    queryKey: ['assistant-memories'],
    queryFn: () => apiClient<MemoryListResponse>('/api/assistant/memories'),
  })
}

/** Forget all preferences. */
export function useForgetMemories() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () =>
      apiClient<void>('/api/assistant/memories', {
        method: 'DELETE',
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['assistant-memories'] })
    },
  })
}

/** Forget a specific preference. */
export function useForgetMemory() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (memoryId: string) =>
      apiClient<void>(`/api/assistant/memories/${memoryId}`, {
        method: 'DELETE',
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['assistant-memories'] })
    },
  })
}

