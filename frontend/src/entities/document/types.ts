import type { components } from '../../shared/api/schema'

export type Document = components['schemas']['Document']
export type DocumentPage = components['schemas']['DocumentPage']
export type DocType = components['schemas']['DocType']
export type DocStatus = components['schemas']['DocStatus']
export type DuplicateInfo = components['schemas']['DuplicateInfo']
export type PageInfo = components['schemas']['PageInfo']
export type RiskLevel = components['schemas']['RiskLevel']
export type Verdict = components['schemas']['Verdict']
export type LedgerMapping = components['schemas']['LedgerMapping']
export type LedgerMappingView = components['schemas']['LedgerMappingView']

export const DOC_TYPE_BADGE: Record<string, { variant: 'brand' | 'clean' | 'evidence' | 'low' | 'outline' | 'default' }> = {
  BANK_STATEMENT: { variant: 'brand' },
  SALES_INVOICE: { variant: 'clean' },
  PURCHASE_INVOICE: { variant: 'evidence' },
  RECEIPT: { variant: 'low' },
  LEDGER_EXPORT: { variant: 'outline' },
}
