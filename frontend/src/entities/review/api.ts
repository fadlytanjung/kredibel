import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '../../shared/api/client'
import type { components } from '../../shared/api/schema'

export type ReviewItem = components['schemas']['ReviewItem']
export type ReviewItemKind = components['schemas']['ReviewItemKind']
export type ReviewItemPage = components['schemas']['ReviewItemPage']
export type ResolveRequest = components['schemas']['ResolveRequest']
export type ResolveAction = components['schemas']['ResolveAction']

// A workspace holds tens to hundreds of open items; the queue pages them on the client (docs/12 §7).
const QUEUE_LIMIT = 500

/** Open review items, highest priority first, with counts per kind (docs/10 §2.5, AC-009-2). */
export function useReviewItems(enabled = true) {
  return useQuery({
    queryKey: ['review-items', 'OPEN'],
    queryFn: () => apiClient<ReviewItemPage>(`/api/review-items?status=OPEN&limit=${QUEUE_LIMIT}`),
    enabled,
  })
}

export function useReviewItem(itemId: string | undefined) {
  return useQuery({
    queryKey: ['review-item', itemId],
    queryFn: () => apiClient<ReviewItem>(`/api/review-items/${itemId}`),
    enabled: Boolean(itemId),
  })
}

/** Resolve with one allowed action; the item's month is reconciled again (AC-009-5, AC-009-6). */
export function useResolveReviewItem() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ itemId, request }: { itemId: string; request: ResolveRequest }) =>
      apiClient<ReviewItem>(`/api/review-items/${itemId}/resolve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(request),
      }),
    onSuccess: (item) => {
      queryClient.setQueryData(['review-item', item.itemId], item)
      void queryClient.invalidateQueries({ queryKey: ['review-items'] })
      void queryClient.invalidateQueries({ queryKey: ['months'] })
      if (item.month) void queryClient.invalidateQueries({ queryKey: ['month', item.month] })
    },
  })
}
