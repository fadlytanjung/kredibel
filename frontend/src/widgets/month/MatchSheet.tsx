/**
 * Manual Match Sheet for Bank Lines (spec 007, ADR-025).
 *
 * Allows a user to:
 * 1. Review candidate invoices/receipts matching direction and closest amount.
 * 2. Select any document available in that month.
 * 3. Link the selected document to the bank line.
 * 4. Or mark the bank line as needing no document (SUPPORT_NOT_REQUIRED decision).
 */

import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useBankLineAiSuggestion } from '../../entities/assistant'
import { type BankLine, CASHFLOW_BADGE, isIncoming } from '../../entities/bank-line'
import { useCreateDecision } from '../../entities/decision'
import { useCreateMatch } from '../../entities/match'
import { formatDate } from '../../shared/lib/formatDate'
import { formatAmount } from '../../shared/lib/formatMoney'
import { Badge, Button, Icon } from '../../shared/ui'
import type { Payment, Row } from './useMonthDocuments'

const FULL_PAID: Payment[] = ['PAID_BANK', 'CONFIRMED_BY_YOU', 'PAID_CASH']

export interface MatchSheetProps {
  line: BankLine
  month: string
  currency: string
  documents: Row[]
  onClose: () => void
  onMatched?: (docIdentifier: string) => void
  onNotRequired?: () => void
}

interface ScoredCandidate {
  doc: Row
  gap: number
  isExact: boolean
  isClose: boolean
}

export function MatchSheet({
  line,
  month,
  currency,
  documents,
  onClose,
  onMatched,
  onNotRequired,
}: MatchSheetProps) {
  const { t } = useTranslation(['months', 'common', 'assistant'])
  const createMatchMutation = useCreateMatch()
  const createDecisionMutation = useCreateDecision()
  const { data: aiSuggestion, isLoading: loadingAi } = useBankLineAiSuggestion(line.txId)

  const [selectedDocId, setSelectedDocId] = useState<string>('')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const incoming = isIncoming(line)
  const lineAmt = Math.abs(Number(line.amount.amount || 0))

  // Esc key closes the sheet
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [onClose])

  // Filter documents by direction
  const eligibleDocs = useMemo(() => {
    return documents.filter((doc) => {
      if (incoming) {
        return doc.kind === 'SALES'
      }
      return doc.kind === 'PURCHASE' || doc.kind === 'RECEIPT'
    })
  }, [documents, incoming])

  // Score and rank candidates
  const scoredCandidates = useMemo<ScoredCandidate[]>(() => {
    return eligibleDocs
      .map((doc) => {
        const docAmt = Number(doc.total?.amount ?? 0)
        const gap = lineAmt > 0 ? Math.abs(lineAmt - docAmt) / lineAmt : Math.abs(docAmt)
        const isExact = Math.abs(lineAmt - docAmt) < 0.005
        const isClose = gap <= 0.1
        return { doc, gap, isExact, isClose }
      })
      .sort((a, b) => {
        // Unpaid first
        const aUnpaid = !FULL_PAID.includes(a.doc.payment) ? 0 : 1
        const bUnpaid = !FULL_PAID.includes(b.doc.payment) ? 0 : 1
        if (aUnpaid !== bUnpaid) return aUnpaid - bUnpaid
        // Exact match first
        if (a.isExact !== b.isExact) return a.isExact ? -1 : 1
        // Closest amount next
        if (Math.abs(a.gap - b.gap) > 0.001) return a.gap - b.gap
        // Date proximity
        return (a.doc.date ?? '').localeCompare(b.doc.date ?? '')
      })
  }, [eligibleDocs, lineAmt])

  // Top candidates to recommend
  const topCandidates = useMemo(() => {
    return scoredCandidates.filter((c) => c.isClose || !FULL_PAID.includes(c.doc.payment)).slice(0, 4)
  }, [scoredCandidates])

  const selectedCandidate = useMemo(() => {
    return eligibleDocs.find((d) => d.id === selectedDocId)
  }, [eligibleDocs, selectedDocId])

  const handleLink = async () => {
    if (!selectedCandidate) return
    setErrorMessage(null)
    try {
      const isReceipt = selectedCandidate.kind === 'RECEIPT'
      await createMatchMutation.mutateAsync({
        bankLineIds: [line.txId],
        ...(isReceipt ? { receiptIds: [selectedCandidate.id] } : { invoiceIds: [selectedCandidate.id] }),
      })
      onMatched?.(selectedCandidate.number || selectedCandidate.id)
      onClose()
    } catch {
      setErrorMessage(t('months:monthDetail.matchFailed'))
    }
  }

  const handleNoDocumentNeeded = async () => {
    setErrorMessage(null)
    try {
      await createDecisionMutation.mutateAsync({
        kind: 'SUPPORT_NOT_REQUIRED',
        txId: line.txId,
        reason: 'No supporting document is needed for this line.',
      })
      onNotRequired?.()
      onClose()
    } catch {
      setErrorMessage(t('months:monthDetail.matchFailed'))
    }
  }

  const busy = createMatchMutation.isPending || createDecisionMutation.isPending

  return (
    <div className="flow-sheet">
      <button type="button" className="scrim" aria-label={t('common:actions.close', { defaultValue: 'Close' })} onClick={onClose} />
      <section className="sheet" role="dialog" aria-modal="true" aria-labelledby="match-sheet-h">
        <div className="sheet-head">
          <div>
            <h2 id="match-sheet-h">{t('months:monthDetail.matchSheet.title', { defaultValue: 'Match bank transaction' })}</h2>
            <p className="muted small">{line.month || month}</p>
          </div>
          <button type="button" className="icon-button" aria-label={t('common:actions.close', { defaultValue: 'Close' })} onClick={onClose}>
            <Icon name="x" />
          </button>
        </div>

        <div className="sheet-body stack gap-5">
          {/* Target Transaction Summary Card */}
          <div className="subject">
            <span className="ico">
              <Icon name="bank" />
            </span>
            <span className="t">{line.description}</span>
            <span className={`amt ${incoming ? 'amt-in' : 'amt-out'}`}>
              {incoming ? '+' : ''}
              {formatAmount(line.amount?.amount ?? '0', { currency })}
            </span>
            <div className="s row gap-2 items-center flex-wrap mt-1">
              {line.date && <span>{formatDate(line.date)}</span>}
              {line.category && (
                <Badge variant={CASHFLOW_BADGE[line.cashflowClass ?? 'UNCLASSIFIED']}>
                  {t(`months:categories.${line.category}`, { defaultValue: line.category })}
                </Badge>
              )}
              {line.cashflowClass && line.cashflowClass !== 'UNCLASSIFIED' && (
                <Badge variant="outline">
                  {t('months:ifrsLabel', { classification: t(`months:cashflow.${line.cashflowClass}`) })}
                </Badge>
              )}
            </div>
          </div>

          <p className="muted small">
            {t(
              'months:monthDetail.matchSheet.instruction',
              { defaultValue: 'Select a supporting invoice or receipt for this transaction, or mark it as needing no document.' },
            )}
          </p>

          {errorMessage && (
            <div className="badge badge-critical" role="alert">
              {errorMessage}
            </div>
          )}

          {/* AI Match Analysis Card */}
          {loadingAi ? (
            <div className="row items-center gap-2 p-3 rounded-md bg-canvas border border-line">
              <Icon name="sparkles" size="sm" className="spin" />
              <span className="muted small">{t('assistant:matchSuggestion.analyzing')}</span>
            </div>
          ) : aiSuggestion ? (
            <div className="stack gap-2 p-3 rounded-md bg-canvas border border-line">
              <div className="row items-center justify-between">
                <span className="row items-center gap-2 font-semibold text-xs">
                  <Icon name="sparkles" size="sm" />
                  {t('assistant:matchSuggestion.title')}
                </span>
                {aiSuggestion.confidence > 0 && (
                  <Badge variant={aiSuggestion.confidence >= 0.8 ? 'clean' : 'evidence'}>
                    {Math.round(aiSuggestion.confidence * 100)}% {t('assistant:matchSuggestion.confidence')}
                  </Badge>
                )}
              </div>

              {aiSuggestion.reason && (
                <p className="muted small m-0 leading-relaxed">
                  {aiSuggestion.reason}
                </p>
              )}

              {aiSuggestion.recommendedDocId && (
                <div className="row items-center justify-between mt-1">
                  <span className="small font-medium text-ink-muted">
                    {t('assistant:matchSuggestion.recommended')}: <code>{aiSuggestion.recommendedDocId}</code>
                  </span>
                  {selectedDocId !== aiSuggestion.recommendedDocId && (
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => setSelectedDocId(aiSuggestion.recommendedDocId!)}
                    >
                      {t('assistant:matchSuggestion.selectRecommended')}
                    </Button>
                  )}
                </div>
              )}

              {aiSuggestion.missingDocumentAdvice && !aiSuggestion.recommendedDocId && (
                <div className="row items-center gap-2 mt-1 muted small">
                  <Icon name="info" size="sm" />
                  <span>{aiSuggestion.missingDocumentAdvice}</span>
                </div>
              )}
            </div>
          ) : null}

          {/* Top Candidates Section */}
          <div className="stack gap-3">
            <h3 className="type-h4">
              {t('months:monthDetail.matchSheet.candidatesTitle', { defaultValue: 'Suggested documents' })}
            </h3>

            {topCandidates.length > 0 ? (
              <div
                className="candidates"
                role="radiogroup"
                aria-label={t('months:monthDetail.matchSheet.candidatesTitle', { defaultValue: 'Suggested documents' })}
              >
                {topCandidates.map(({ doc, isExact }) => {
                  const isPicked = selectedDocId === doc.id
                  const isRcp = doc.kind === 'RECEIPT'
                  const title = doc.number
                    ? isRcp
                      ? t('months:monthDetail.docs.receipt', { number: doc.number, defaultValue: `Receipt ${doc.number}` })
                      : t('months:monthDetail.docs.invoice', { number: doc.number, defaultValue: `Invoice ${doc.number}` })
                    : isRcp
                      ? t('months:monthDetail.docs.receiptNoNumber', { defaultValue: 'Receipt (no number)' })
                      : t('months:monthDetail.docs.invoiceNoNumber', { defaultValue: 'Invoice (no number)' })

                  return (
                    <div
                      key={doc.id}
                      className={`candidate ${isPicked ? 'is-picked' : ''}`}
                      role="radio"
                      aria-checked={isPicked}
                      tabIndex={0}
                      onClick={() => setSelectedDocId(doc.id)}
                      onKeyDown={(e) => {
                        if (e.key === ' ' || e.key === 'Enter') {
                          e.preventDefault()
                          setSelectedDocId(doc.id)
                        }
                      }}
                    >
                      <span className="radio" />
                      <div>
                        <div className="row items-center gap-2 flex-wrap">
                          <span className="t">{title}</span>
                          <Badge variant={doc.kind === 'SALES' ? 'clean' : doc.kind === 'PURCHASE' ? 'evidence' : 'low'}>
                            {doc.kind === 'SALES'
                              ? t('months:monthDetail.docs.badgeSales')
                              : doc.kind === 'PURCHASE'
                                ? t('months:monthDetail.docs.badgePurchase')
                                : t('months:monthDetail.docs.badgeReceipt')}
                          </Badge>
                          {isExact && (
                            <span className="why-tag yes">
                              <Icon name="check" size="sm" />
                              {t('months:monthDetail.matchSheet.exactMatch', { defaultValue: 'Exact amount' })}
                            </span>
                          )}
                        </div>
                        <div className="s mt-1">
                          {[doc.party, doc.date && formatDate(doc.date)].filter(Boolean).join(' • ')}
                        </div>
                      </div>
                      <span className="amt">
                        {doc.total ? formatAmount(doc.total.amount, { currency: doc.total.currency }) : '—'}
                      </span>
                    </div>
                  )
                })}
              </div>
            ) : (
              <p className="muted small">
                {t(
                  'months:monthDetail.matchSheet.noCandidates',
                  { defaultValue: 'No documents with matching amounts found this month.' },
                )}
              </p>
            )}
          </div>

          {/* Fallback Selector for All Eligible Month Documents */}
          <div className="stack gap-2">
            <label htmlFor="all-month-docs" className="type-h4">
              {t(
                'months:monthDetail.matchSheet.allDocsTitle',
                { month: line.month || month, defaultValue: `Or select any document in ${line.month || month}` },
              )}
            </label>
            <select
              id="all-month-docs"
              className="select"
              value={selectedDocId}
              onChange={(e) => setSelectedDocId(e.target.value)}
            >
              <option value="">
                {t('months:monthDetail.matchSheet.allDocsPlaceholder', { defaultValue: 'Choose a document...' })}
              </option>
              {eligibleDocs.map((doc) => {
                const isRcp = doc.kind === 'RECEIPT'
                const docTitle = doc.number
                  ? isRcp
                    ? t('months:monthDetail.docs.receipt', { number: doc.number, defaultValue: `Receipt ${doc.number}` })
                    : t('months:monthDetail.docs.invoice', { number: doc.number, defaultValue: `Invoice ${doc.number}` })
                  : isRcp
                    ? t('months:monthDetail.docs.receiptNoNumber', { defaultValue: 'Receipt' })
                    : t('months:monthDetail.docs.invoiceNoNumber', { defaultValue: 'Invoice' })
                const party = doc.party || t('months:monthDetail.docs.unknownParty', { defaultValue: 'Unknown' })
                const amt = doc.total
                  ? formatAmount(doc.total.amount, { currency: doc.total.currency })
                  : t('months:monthDetail.noValue')
                return (
                  <option key={doc.id} value={doc.id}>
                    {`${docTitle} — ${party} (${amt})`}
                  </option>
                )
              })}
            </select>
          </div>

          {/* Action to Mark as No Document Needed */}
          <div className="panel panel-pad stack gap-2 mt-2">
            <h4 className="type-h4">
              {t('months:monthDetail.matchSheet.noDocTitle', { defaultValue: 'Does this transaction need no document?' })}
            </h4>
            <p className="muted small">
              {t(
                'months:monthDetail.matchSheet.noDocHint',
                {
                  defaultValue:
                    'Rent without an invoice, bank charges, tax payments, owner drawings, and cash expenses can be marked as not needing a document.',
                },
              )}
            </p>
            <div>
              <Button
                variant="secondary"
                size="sm"
                disabled={busy}
                onClick={() => void handleNoDocumentNeeded()}
              >
                {t('months:monthDetail.matchSheet.noDocAction', { defaultValue: 'No document needed' })}
              </Button>
            </div>
          </div>

          {/* Footer Actions */}
          <div className="row gap-3 justify-end mt-4">
            <Button variant="secondary" disabled={busy} onClick={onClose}>
              {t('months:monthDetail.cancel', { defaultValue: 'Cancel' })}
            </Button>
            <Button
              variant="primary"
              disabled={!selectedDocId || busy}
              onClick={() => void handleLink()}
            >
              {busy ? (
                t('common:actions.saving', { defaultValue: 'Saving...' })
              ) : (
                t('months:monthDetail.matchSheet.linkAction', { defaultValue: 'Link document' })
              )}
            </Button>
          </div>
        </div>
      </section>
    </div>
  )
}
