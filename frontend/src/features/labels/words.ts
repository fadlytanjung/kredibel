/** How a label's value, source and model read on screen (shared by the page and the panel). */

import type { TFunction } from 'i18next'
import type { Label } from '../../entities/label'

export const DOC_TYPES = ['BANK_STATEMENT', 'SALES_INVOICE', 'PURCHASE_INVOICE', 'RECEIPT', 'LEDGER_EXPORT', 'OTHER']
export const PAGE_TYPES = ['STATEMENT_SUMMARY', 'STATEMENT_TRANSACTIONS', 'TERMS_OR_COVER', 'INVOICE', 'RECEIPT', 'LEDGER', 'OTHER']
export const ROLES = ['CLIENT', 'SUPPLIER', 'LENDER', 'OWNER', 'OWN_ACCOUNT', 'RELATED_PARTY', 'GOVERNMENT', 'OTHER']

export function valueWord(t: TFunction, task: Label['task'], value: string): string {
  switch (task) {
    case 'CATEGORY':
      return t(`months:categories.${value}`, { defaultValue: value })
    case 'DOC_TYPE':
      return t(`documents:detail.docType.${value}`, { defaultValue: value })
    case 'PAGE_TYPE':
      return t(`labels:pageTypes.${value}`, { defaultValue: value })
    case 'COUNTERPARTY_ROLE':
      return t(`labels:roles.${value}`, { defaultValue: value })
    default:
      return value
  }
}

/** "gemini-2.5-flash-lite" reads as "Flash-Lite", the way people name the models. */
export function shortModel(model: string | null | undefined): string {
  if (!model) return ''
  const id = model.toLowerCase()
  if (id.includes('flash-lite')) return 'Flash-Lite'
  if (id.includes('flash')) return 'Flash'
  if (id.includes('pro')) return 'Pro'
  return model
}

export function sourceWord(t: TFunction, label: Label): string {
  const ai = label.ai
  if (!ai) return ''
  if (ai.source === 'MODEL') {
    return ai.model && ai.promptVersion
      ? t('labels:sources.MODEL', { model: shortModel(ai.model), prompt: ai.promptVersion })
      : t('labels:sources.MODEL_NO_VERSION')
  }
  return t(`labels:sources.${ai.source}`)
}

export function statusKey(label: Label): 'needs' | 'proposed' | 'verified' | 'corrected' {
  if (label.status === 'VERIFIED') return 'verified'
  if (label.status === 'CORRECTED') return 'corrected'
  return label.needsCheck ? 'needs' : 'proposed'
}

export function confidenceLevel(confidence: number | null | undefined): 'lo' | 'mid' | 'hi' | 'none' {
  if (confidence === null || confidence === undefined) return 'none'
  return confidence < 0.7 ? 'lo' : confidence < 0.9 ? 'mid' : 'hi'
}

export const compact = (n: number) => n.toLocaleString('en')
