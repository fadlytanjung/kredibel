import type { TFunction } from 'i18next'
import type { Transaction } from '../../entities/transactions'

/** Who chose the category: a person, the match, a rule, or the model with its confidence. */
export function categorizedBy(tx: Transaction, t: TFunction<'transactions'>): string {
  const by = tx.categorizedBy ?? 'NONE'
  if (by === 'MODEL') {
    return tx.categoryConfidence ? t('by.MODEL', { confidence: Math.round(Number(tx.categoryConfidence) * 100) }) : t('by.MODEL_plain')
  }
  return t(`by.${by}`)
}
