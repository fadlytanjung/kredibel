import { useQuery } from '@tanstack/react-query'
import { apiClient } from '../../shared/api/client'
import type { components } from '../../shared/api/schema'

export type Invoice = components['schemas']['Invoice']
export type Receipt = components['schemas']['Receipt']
export type InvoicePage = components['schemas']['InvoicePage']
export type ReceiptPage = components['schemas']['ReceiptPage']
export type ValueReading = components['schemas']['ValueReading']

/** A value pointed at on the page: which record field, on which page, inside which box. */
export interface ValueFocus {
  key: string
  page: number
  bbox: { x0: number; y0: number; x1: number; y1: number }
}

/** The invoices read from one document; a PDF can hold several (docs/10 §2.4). */
export function useInvoices(docId: string | undefined) {
  return useQuery({
    queryKey: ['invoices', { docId }],
    queryFn: () => apiClient<InvoicePage>(`/api/invoices?docId=${encodeURIComponent(docId ?? '')}`),
    enabled: Boolean(docId),
  })
}

export function useReceipts(docId: string | undefined) {
  return useQuery({
    queryKey: ['receipts', { docId }],
    queryFn: () => apiClient<ReceiptPage>(`/api/receipts?docId=${encodeURIComponent(docId ?? '')}`),
    enabled: Boolean(docId),
  })
}

/** A month's invoices and receipts, with their payment evidence (docs/10 §2.4). */
export function useMonthInvoices(month: string | undefined) {
  return useQuery({
    queryKey: ['invoices', { month }],
    queryFn: () => apiClient<InvoicePage>(`/api/invoices?month=${encodeURIComponent(month ?? '')}`),
    enabled: Boolean(month),
  })
}

export function useMonthReceipts(month: string | undefined) {
  return useQuery({
    queryKey: ['receipts', { month }],
    queryFn: () => apiClient<ReceiptPage>(`/api/receipts?month=${encodeURIComponent(month ?? '')}`),
    enabled: Boolean(month),
  })
}

/** The focus for one field of a record, when the reading has a box. */
export function focusOf(
  recordId: string,
  field: string,
  reading: ValueReading | undefined,
): ValueFocus | undefined {
  if (!reading?.bbox || !reading.page) return undefined
  return { key: `${recordId}:${field}`, page: reading.page, bbox: reading.bbox }
}
