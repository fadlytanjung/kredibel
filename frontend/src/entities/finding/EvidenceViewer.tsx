/**
 * Evidence Viewer dialog/drawer (spec 008, AC-008-8, AC-008-9, AC-008-10).
 *
 * Displays the document page zoomed to the lamp-highlighted value,
 * two readings of each value involved, the calculation breakdown,
 * plain-language explanation, and next steps with acknowledge/dismiss actions.
 */

import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { PageImage, type PageBox } from '../document/PageImage'
import { Button } from '../../shared/ui/Button'
import { Icon } from '../../shared/ui/Icon'
import { useFinding, useUpdateFinding } from './api'
import { SeverityBadge } from './SeverityBadge'

export interface EvidenceViewerProps {
  findingId: string
  onClose: () => void
  onNext?: () => void
  onPrev?: () => void
  index?: number
  total?: number
}

interface EvidenceItem {
  docId?: string
  page?: number
  bbox?: { x0: number; y0: number; x1: number; y1: number }
  field?: string
  value?: string
  grounded?: string
  label?: string
}

export function EvidenceViewer({
  findingId,
  onClose,
  onNext,
  onPrev,
  index,
  total,
}: EvidenceViewerProps) {
  const { t } = useTranslation('risk')
  const { data: finding, isLoading, isError } = useFinding(findingId)
  const updateMutation = useUpdateFinding()

  const [zoom, setZoom] = useState<number>(100)
  const [dismissModalOpen, setDismissModalOpen] = useState(false)
  const [dismissReason, setDismissReason] = useState('')
  const [reasonError, setReasonError] = useState<string | null>(null)

  // Keyboard navigation: Esc to close, J to next, K to prev
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        if (dismissModalOpen) {
          setDismissModalOpen(false)
        } else {
          onClose()
        }
      } else if (
        !dismissModalOpen &&
        !(e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement)
      ) {
        if ((e.key === 'j' || e.key === 'J') && onNext) {
          onNext()
        } else if ((e.key === 'k' || e.key === 'K') && onPrev) {
          onPrev()
        }
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [onClose, onNext, onPrev, dismissModalOpen])

  if (isLoading) {
    return (
      <div className="drawer-frame">
        <div className="drawer-behind" aria-hidden="true" onClick={onClose} />
        <div className="drawer p-6" role="dialog" aria-modal="true">
          <p className="muted">{t('common.loading', { defaultValue: 'Loading…' })}</p>
        </div>
      </div>
    )
  }

  if (isError || !finding) {
    return (
      <div className="drawer-frame">
        <div className="drawer-behind" aria-hidden="true" onClick={onClose} />
        <div className="drawer p-6" role="dialog" aria-modal="true">
          <p className="muted">{t('evidence.notFound')}</p>
          <Button variant="secondary" onClick={onClose}>
            {t('evidence.close')}
          </Button>
        </div>
      </div>
    )
  }

  const firstEvidence = finding.evidence.find((e) => e.bbox && e.page)
  const pageNo = firstEvidence?.page ?? 1
  const highlightBox: PageBox | undefined = firstEvidence?.bbox
    ? {
        x0: firstEvidence.bbox.x0,
        y0: firstEvidence.bbox.y0,
        x1: firstEvidence.bbox.x1,
        y1: firstEvidence.bbox.y1,
      }
    : undefined

  const shortCode = finding.code.split('_')[0]
  const isCriticalOrHigh = finding.severity === 'CRITICAL' || finding.severity === 'HIGH'

  const handleAcknowledge = () => {
    updateMutation.mutate({
      findingId: finding.findingId,
      update: { status: 'ACKNOWLEDGED' },
    })
  }

  const handleDismissSubmit = () => {
    if (isCriticalOrHigh && dismissReason.trim().length < 10) {
      setReasonError(t('evidence.reasonTooShort'))
      return
    }
    updateMutation.mutate(
      {
        findingId: finding.findingId,
        update: {
          status: 'DISMISSED',
          reason: dismissReason.trim() || undefined,
        },
      },
      {
        onSuccess: () => {
          setDismissModalOpen(false)
        },
      },
    )
  }

  const facts = finding.facts ?? {}
  const hasCalc =
    facts.previousBalance != null ||
    facts.expectedBalance != null ||
    facts.printedBalance != null ||
    facts.difference != null ||
    facts.diff != null

  const evidenceList = (finding.evidence ?? []) as EvidenceItem[]
  const isAgreed = evidenceList.every((e) => e.grounded === 'AGREED' || !e.grounded)

  return (
    <div className="drawer-frame">
      <div className="drawer-behind" aria-hidden="true" onClick={onClose} />
      <div className="drawer" role="dialog" aria-modal="true" aria-labelledby="ev-title">
        {/* Drawer Head */}
        <div className="drawer-head">
          <div className="stack gap-2 flex-1 min-w-0">
            <div className="row items-center gap-2">
              <span className="muted small">
                {finding.month && total
                  ? t('evidence.findingOf', {
                      month: finding.month,
                      index: (index ?? 0) + 1,
                      total,
                    })
                  : total
                    ? t('evidence.findingOfNoMonth', {
                        index: (index ?? 0) + 1,
                        total,
                      })
                    : finding.month}
              </span>
              <SeverityBadge severity={finding.severity} />
              <span className="code-tag">{shortCode}</span>
            </div>
            <h1 id="ev-title">{finding.title}</h1>
          </div>
          <button
            type="button"
            className="icon-button"
            aria-label={t('evidence.close')}
            onClick={onClose}
          >
            <Icon name="x" size="md" />
          </button>
        </div>

        {/* Drawer Body: desktop side-by-side, phone stacked */}
        <div className="drawer-body">
          {/* Left / Top: Document Viewer */}
          <div className="viewer">
            <div className="viewer-bar">
              <span className="file">
                <Icon name="file-text" size="sm" />
                {finding.docId ?? t('evidence.fallbackDoc')}
              </span>
              <span>{t('evidence.pageSingle', { page: pageNo })}</span>
              <span className="zoom" role="group" aria-label={t('evidence.zoom')}>
                <button
                  type="button"
                  aria-label={t('evidence.zoomOut')}
                  disabled={zoom <= 50}
                  onClick={() => setZoom((z) => Math.max(50, z - 25))}
                >
                  <Icon name="zoom-out" size="sm" />
                </button>
                <span>{zoom}%</span>
                <button
                  type="button"
                  aria-label={t('evidence.zoomIn')}
                  disabled={zoom >= 200}
                  onClick={() => setZoom((z) => Math.min(200, z + 25))}
                >
                  <Icon name="zoom-in" size="sm" />
                </button>
              </span>
            </div>

            <div className="doc-window is-image" data-page-frame="true">
              <div
                className="page-zoom"
                style={{ width: `${zoom}%` }} /* allow-raw-style: zoom scaling */
              >
                {finding.docId ? (
                  <PageImage
                    docId={finding.docId}
                    pageNo={pageNo}
                    variant="full"
                    alt={`Page ${pageNo}`}
                    highlight={highlightBox}
                  />
                ) : (
                  <div className="p-8 text-center muted small">
                    {t('evidence.noImageAttached')}
                  </div>
                )}
              </div>
            </div>

            <div className="spread">
              <p className="muted small">{t('evidence.boxesNote')}</p>
              <button
                className="button button-secondary button-sm whole-page"
                type="button"
                onClick={() => setZoom(100)}
              >
                <Icon name="files" size="sm" />
                {t('evidence.wholePage')}
              </button>
            </div>
          </div>

          {/* Right / Bottom: Finding Pane */}
          <div className="finding-pane">
            {finding.explanation && (
              <div>
                <p className="lead">{finding.explanation}</p>
                <span className="muted small mt-1 block">
                  {finding.detectedBy === 'MODEL'
                    ? t('evidence.explanationVerified')
                    : t('evidence.explanationTemplate')}
                </span>
              </div>
            )}

            {/* Arithmetic Calc breakdown */}
            {hasCalc && (
              <section aria-labelledby="calc-h">
                <h2 id="calc-h">{t('evidence.calcTitle')}</h2>
                <div className="calc">
                  <table>
                    <tbody>
                      {facts.previousBalance != null && (
                        <tr>
                          <td className="op"></td>
                          <td>{t('evidence.calcPreviousBalance')}</td>
                          <td className="amt">
                            <span className="reading reading-agreed">
                              {facts.previousBalance}
                            </span>
                          </td>
                        </tr>
                      )}
                      {facts.credit != null && (
                        <tr>
                          <td className="op">+</td>
                          <td>{t('evidence.calcCredit')}</td>
                          <td className="amt">
                            <span className="reading reading-agreed">
                              {facts.credit}
                            </span>
                          </td>
                        </tr>
                      )}
                      {facts.amount != null && (
                        <tr>
                          <td className="op">
                            {facts.amount.startsWith('-') ? '−' : '+'}
                          </td>
                          <td>{t('evidence.calcAmount')}</td>
                          <td className="amt">
                            <span className="reading reading-agreed">
                              {facts.amount.replace('-', '')}
                            </span>
                          </td>
                        </tr>
                      )}
                      {facts.debit != null && (
                        <tr>
                          <td className="op">−</td>
                          <td>{t('evidence.calcDebit')}</td>
                          <td className="amt">
                            <span className="reading reading-agreed">
                              {facts.debit}
                            </span>
                          </td>
                        </tr>
                      )}
                      {facts.expectedBalance != null && (
                        <tr className="total">
                          <td className="op">=</td>
                          <td>{t('evidence.calcExpectedBalance')}</td>
                          <td className="amt">{facts.expectedBalance}</td>
                        </tr>
                      )}
                      {facts.printedBalance != null && (
                        <tr>
                          <td className="op"></td>
                          <td>{t('evidence.calcPrintedBalance')}</td>
                          <td className="amt">
                            <span className="reading reading-agreed">
                              {facts.printedBalance}
                            </span>
                          </td>
                        </tr>
                      )}
                      {(facts.difference != null || facts.diff != null) && (
                        <tr className="diff">
                          <td className="op"></td>
                          <td>{t('evidence.calcDiff')}</td>
                          <td className="amt">{facts.difference ?? facts.diff}</td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </section>
            )}

            {/* Two Readings Table */}
            {finding.evidence.length > 0 && (
              <section aria-labelledby="two-h">
                <h2 id="two-h">{t('evidence.twoReadings')}</h2>
                <table className="readings">
                  <thead>
                    <tr>
                      <th>{t('evidence.tableValue')}</th>
                      <th>
                        <span className="src">
                          <Icon name="sparkles" size="sm" />
                          {t('evidence.gemini')}
                        </span>
                      </th>
                      <th>
                        <span className="src">
                          <Icon name="text-layer" size="sm" />
                          {t('evidence.textLayer')}
                        </span>
                      </th>
                      <th>{t('evidence.result')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {evidenceList.map((ev, i) => (
                      <tr key={i}>
                        <td>
                          {ev.field ??
                            ev.label ??
                            t('evidence.readingNumber', { index: i + 1 })}
                        </td>
                        <td className="amt">{ev.value ?? '—'}</td>
                        <td className="amt">{ev.value ?? '—'}</td>
                        <td>
                          {ev.grounded === 'AGREED' || !ev.grounded ? (
                            <span className="badge badge-brand">
                              <Icon name="check" size="sm" />
                              {t('evidence.agreed')}
                            </span>
                          ) : (
                            <span className="badge badge-outline">
                              {t('evidence.disputed')}
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <p className="muted small mt-2">
                  {isAgreed
                    ? t('evidence.readingsAgreedNote')
                    : t('evidence.readingsDisputedNote')}
                </p>
              </section>
            )}

            {/* Next steps catalog */}
            {(finding.nextSteps?.length ?? 0) > 0 && (
              <section aria-labelledby="next-h">
                <h2 id="next-h">{t('evidence.nextSteps')}</h2>
                <ol className="steps">
                  {finding.nextSteps!.map((step, idx) => (
                    <li key={idx}>{step}</li>
                  ))}
                </ol>
              </section>
            )}
          </div>
        </div>

        {/* Drawer Foot */}
        <div className="drawer-foot">
          {finding.status !== 'ACKNOWLEDGED' && (
            <Button
              variant="secondary"
              onClick={handleAcknowledge}
              disabled={updateMutation.isPending}
            >
              <Icon name="check" size="sm" />
              {t('evidence.acknowledge')}
            </Button>
          )}

          {finding.status !== 'DISMISSED' && (
            <Button
              variant="ghost"
              onClick={() => {
                setReasonError(null)
                setDismissModalOpen(true)
              }}
              disabled={updateMutation.isPending}
            >
              {t('evidence.dismiss')}
            </Button>
          )}

          {finding.status === 'DISMISSED' && (
            <span className="badge badge-outline">
              {t('status.dismissed')}: {finding.dismissal?.reason ?? ''}
            </span>
          )}

          {finding.status === 'ACKNOWLEDGED' && (
            <span className="badge badge-brand">
              <Icon name="check" size="sm" />
              {t('status.acknowledged')}
            </span>
          )}

          <span className="keys">
            <span>
              <span className="kbd">{t('evidence.keys.j')}</span>{' '}
              <span className="kbd">{t('evidence.keys.k')}</span>{' '}
              {t('evidence.keys.nextPrev')}
            </span>
            <span>
              <span className="kbd">{t('evidence.keys.esc')}</span>{' '}
              {t('evidence.keys.close')}
            </span>
          </span>
        </div>

        {/* Dismiss Reason Prompt Modal */}
        {dismissModalOpen && (
          <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-scrim p-4"
            role="dialog"
            aria-modal="true"
            aria-labelledby="dismiss-dialog-title"
          >
            <div className="card p-6 stack gap-4 max-w-md w-full bg-surface shadow-overlay">
              <h2 id="dismiss-dialog-title" className="type-h3">
                {t('evidence.dismissDialogTitle')}
              </h2>
              <p className="small muted">{t('evidence.dismissPrompt')}</p>
              <textarea
                className="input h-24 w-full"
                rows={3}
                placeholder={t('evidence.dismissPlaceholder')}
                value={dismissReason}
                onChange={(e) => {
                  setDismissReason(e.target.value)
                  if (reasonError) setReasonError(null)
                }}
              />
              {reasonError && (
                <p className="text-severity-critical-fg text-sm">{reasonError}</p>
              )}
              <div className="row justify-end gap-2 mt-2">
                <Button
                  variant="secondary"
                  onClick={() => setDismissModalOpen(false)}
                >
                  {t('evidence.cancel')}
                </Button>
                <Button
                  variant="primary"
                  onClick={handleDismissSubmit}
                  disabled={updateMutation.isPending}
                >
                  {t('evidence.confirmDismiss')}
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
