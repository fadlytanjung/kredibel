/**
 * The fix panel of one review item (spec 009, T009-05, AC-009-4, AC-009-5; docs/11 §6.5): what is
 * wrong, the subject with a link to its page, the suggestion, and only the actions its kind allows.
 */

import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { type BankLine, CASHFLOW_BADGE, useMonthBankLines } from '../../entities/bank-line'
import { type LedgerMapping, PageViewer, useDocument, useLedgerMapping } from '../../entities/document'
import { type Invoice, type Receipt, useMonthInvoices, useMonthReceipts } from '../../entities/record'
import { type ResolveRequest, type ReviewItem, useResolveReviewItem } from '../../entities/review'
import { formatDate } from '../../shared/lib/formatDate'
import { formatAmount } from '../../shared/lib/formatMoney'
import { Badge, Button, Icon } from '../../shared/ui'
import { KIND_ICON, monthName } from './kinds'
import { isComplete } from './mapping'
import { MappingEditor } from './MappingEditor'
import { linesThatCouldPay, subjectsOf } from './subjects'
import { useQueueKeys } from './useQueueKeys'

export interface ItemPanelProps {
  item: ReviewItem
  position: { index: number; total: number }
  onResolved: (item: ReviewItem) => void
  onSkip: () => void
  onClose: () => void
  onPreviewChange?: (hasPreview: boolean) => void
}

function signed(line: BankLine) {
  const amount = Number(line.amount.amount)
  return `${amount > 0 ? '+' : ''}${formatAmount(line.amount.amount, { currency: line.amount.currency })}`
}

function LineSubject({
  line,
  onSeePage,
  activePreviewDocId,
}: {
  line: BankLine
  onSeePage?: (docId: string) => void
  activePreviewDocId?: string | null
}) {
  const { t } = useTranslation(['review', 'months'])
  const isPreviewing = activePreviewDocId === line.docId
  return (
    <div className="subject">
      <span className="ico">
        <Icon name="bank" />
      </span>
      <span className="t">{line.description}</span>
      <span className={`amt ${Number(line.amount.amount) > 0 ? 'amt-in' : ''}`}>{signed(line)}</span>
      <div className="s row gap-2 items-center flex-wrap">
        <span>{formatDate(line.date)}</span>
        {line.category && (
          <Badge variant={CASHFLOW_BADGE[line.cashflowClass ?? 'UNCLASSIFIED']}>
            {t(`months:categories.${line.category}`, { defaultValue: line.category })}
          </Badge>
        )}
        {onSeePage ? (
          <button
            type="button"
            className={`citation button-ghost inline-flex items-center gap-1 text-xs cursor-pointer ${isPreviewing ? 'font-semibold text-brand' : ''}`}
            onClick={() => onSeePage(line.docId)}
            title={t('review:panel.seePage')}
          >
            <Icon name="eye" size="sm" />
            <span>{t('review:panel.seePage')}</span>
          </button>
        ) : (
          <Link className="citation" to={`/documents/${line.docId}`}>
            <Icon name="eye" size="sm" />
            {t('review:panel.seePage')}
          </Link>
        )}
        <Link
          className="citation"
          to={`/documents/${line.docId}`}
          target="_blank"
          rel="noopener noreferrer"
          title={t('review:panel.openDocument')}
        >
          <Icon name="external" size="sm" />
        </Link>
      </div>
    </div>
  )
}

function RecordSubject({
  record,
  onSeePage,
  activePreviewDocId,
}: {
  record: Invoice | Receipt
  onSeePage?: (docId: string) => void
  activePreviewDocId?: string | null
}) {
  const { t } = useTranslation(['review', 'months'])
  const isReceipt = 'receiptId' in record
  const name = isReceipt
    ? record.number
      ? t('months:monthDetail.docs.receipt', { number: record.number })
      : t('months:monthDetail.docs.receiptNoNumber')
    : record.number
      ? t('months:monthDetail.docs.invoice', { number: record.number })
      : t('months:monthDetail.docs.invoiceNoNumber')
  const party = isReceipt ? record.merchantName : record.kind === 'SALES' ? record.buyerName : record.issuerName
  const day = isReceipt ? record.date : record.issueDate
  const isPreviewing = activePreviewDocId === record.docId
  return (
    <div className="subject">
      <span className="ico">
        <Icon name={isReceipt ? 'receipt' : 'file-text'} />
      </span>
      <span className="t">{name}</span>
      <span className="amt">{record.total ? formatAmount(record.total.amount, { currency: record.total.currency }) : '—'}</span>
      <div className="s row gap-2 items-center flex-wrap">
        <span>{[party, day && formatDate(day)].filter(Boolean).join(', ')}</span>
        <Badge variant={isReceipt ? 'low' : record.kind === 'SALES' ? 'clean' : 'evidence'}>
          {isReceipt
            ? t('months:monthDetail.docs.badgeReceipt')
            : record.kind === 'SALES'
              ? t('months:monthDetail.docs.badgeSales')
              : t('months:monthDetail.docs.badgePurchase')}
        </Badge>
        {onSeePage ? (
          <button
            type="button"
            className={`citation button-ghost inline-flex items-center gap-1 text-xs cursor-pointer ${isPreviewing ? 'font-semibold text-brand' : ''}`}
            onClick={() => onSeePage(record.docId)}
            title={t('review:panel.seePage')}
          >
            <Icon name="eye" size="sm" />
            <span>{t('review:panel.seePage')}</span>
          </button>
        ) : (
          <Link className="citation" to={`/documents/${record.docId}`}>
            <Icon name="eye" size="sm" />
            {t('review:panel.seePage')}
          </Link>
        )}
        <Link
          className="citation"
          to={`/documents/${record.docId}`}
          target="_blank"
          rel="noopener noreferrer"
          title={t('review:panel.openDocument')}
        >
          <Icon name="external" size="sm" />
        </Link>
      </div>
    </div>
  )
}

function DocumentSubject({
  docId,
  label,
  onSeePage,
  activePreviewDocId,
}: {
  docId: string
  label: string
  onSeePage?: (docId: string) => void
  activePreviewDocId?: string | null
}) {
  const { t } = useTranslation('review')
  const { data: doc } = useDocument(docId)
  const isPreviewing = activePreviewDocId === docId
  return (
    <div className="subject">
      <span className="ico">
        <Icon name="files" />
      </span>
      <span className="t">{doc?.fileName ?? docId}</span>
      <div className="s row gap-2 items-center flex-wrap">
        <span>{label}</span>
        {onSeePage ? (
          <button
            type="button"
            className={`citation button-ghost inline-flex items-center gap-1 text-xs cursor-pointer ${isPreviewing ? 'font-semibold text-brand' : ''}`}
            onClick={() => onSeePage(docId)}
            title={t('panel.openDocument')}
          >
            <Icon name="eye" size="sm" />
            <span>{t('panel.openDocument')}</span>
          </button>
        ) : (
          <Link className="citation" to={`/documents/${docId}`}>
            <Icon name="eye" size="sm" />
            {t('panel.openDocument')}
          </Link>
        )}
        <Link
          className="citation"
          to={`/documents/${docId}`}
          target="_blank"
          rel="noopener noreferrer"
          title={t('panel.openDocument')}
        >
          <Icon name="external" size="sm" />
        </Link>
      </div>
    </div>
  )
}

function Proposal({ item }: { item: ReviewItem }) {
  const { t } = useTranslation(['review', 'months'])
  const candidate = item.suggestion?.candidates?.[0]
  if (!candidate) return null
  const score = Number(candidate.score ?? 0)
  return (
    <div className="candidates" role="radiogroup" aria-label={t('panel.proposal')}>
      <div className="candidate is-picked" role="radio" aria-checked="true" tabIndex={0}>
        <span className="radio" />
        <span>
          <span className="t">{t('panel.proposal')}</span>
        </span>
        <span className="why">
          {(candidate.reasons ?? []).map((reason) => (
            <span key={reason} className="why-tag yes">
              <Icon name="check" size="sm" />
              {t(`months:monthDetail.matchReasons.${reason}`, { defaultValue: reason })}
            </span>
          ))}
        </span>
        <span className="score">
          {t('panel.fit')}
          <span className="meter-bar">
            <i style={{ width: `${Math.round(score * 100)}%` }} /* allow-raw-style: computed fit meter width */ />
          </span>
          <span>{score.toFixed(2)}</span>
        </span>
      </div>
    </div>
  )
}

function LinePicker({ lines, picked, onPick }: { lines: BankLine[]; picked?: string; onPick: (txId: string) => void }) {
  const { t } = useTranslation('review')
  if (lines.length === 0) return <p className="muted small">{t('panel.noLineFits')}</p>
  return (
    <div className="candidates" role="radiogroup" aria-label={t('panel.linesThatFit')}>
      {lines.map((line) => (
        <div
          key={line.txId}
          className={`candidate ${picked === line.txId ? 'is-picked' : ''}`}
          role="radio"
          aria-checked={picked === line.txId}
          tabIndex={0}
          onClick={() => onPick(line.txId)}
          onKeyDown={(e) => {
            if (e.key === ' ') {
              e.preventDefault()
              onPick(line.txId)
            }
          }}
        >
          <span className="radio" />
          <span>
            <span className="t">{line.description}</span>
            <br />
            <span className="s">{formatDate(line.date)}</span>
          </span>
          <span className="amt">{signed(line)}</span>
        </div>
      ))}
    </div>
  )
}

export function ItemPanel({
  item,
  position,
  onResolved,
  onSkip,
  onClose,
  onPreviewChange,
}: ItemPanelProps) {
  const { t } = useTranslation('review')
  const month = item.month ?? undefined
  const { data: lineData } = useMonthBankLines(month)
  const { data: invoiceData } = useMonthInvoices(month)
  const { data: receiptData } = useMonthReceipts(month)
  const resolve = useResolveReviewItem()
  const [picked, setPicked] = useState<string>()
  const [reasonOpen, setReasonOpen] = useState(false)
  const [reason, setReason] = useState('')
  const [correcting, setCorrecting] = useState(false)
  const [correction, setCorrection] = useState('')
  // A ledger export's column mapping (T005-11): the proposal, then what the person changed.
  const isMapping = item.kind === 'CONFIRM_LEDGER_MAPPING'
  const mappingDocId = isMapping ? item.docId || item.subject.docIds?.[0] : undefined
  const { data: mappingView, isLoading: mappingLoading } = useLedgerMapping(mappingDocId)
  const [edited, setEdited] = useState<LedgerMapping | null>(null)
  const mapping = edited ?? mappingView?.mapping ?? null

  const monthLines = useMemo(() => lineData?.items ?? [], [lineData?.items])
  const subjects = useMemo(
    () =>
      subjectsOf(item, {
        lines: monthLines,
        invoices: invoiceData?.items ?? [],
        receipts: receiptData?.items ?? [],
      }),
    [item, monthLines, invoiceData?.items, receiptData?.items],
  )
  const documents = useMemo(() => [...subjects.invoices, ...subjects.receipts], [subjects.invoices, subjects.receipts])
  const candidates = item.kind === 'UNMATCHED_DOCUMENT' && documents[0] ? linesThatCouldPay(documents[0], monthLines) : []
  const allowed = new Set(item.allowedActions)
  const pickedLine = candidates.find((l) => l.txId === picked) ?? candidates[0]

  const initialDocId =
    item.docId ||
    item.subject.docIds?.[0] ||
    (documents[0] ? ('invoiceId' in documents[0] ? documents[0].docId : documents[0].docId) : null) ||
    subjects.lines[0]?.docId ||
    null

  const [userToggledDocId, setUserToggledDocId] = useState<string | null>(null)
  const [prevItemId, setPrevItemId] = useState(item.itemId)
  if (prevItemId !== item.itemId) {
    setPrevItemId(item.itemId)
    setUserToggledDocId(null)
  }

  const isAutoPreview = item.kind === 'LOW_CONFIDENCE_VALUE' || item.kind === 'POSSIBLE_DUPLICATE'
  const previewDocId =
    userToggledDocId !== null
      ? userToggledDocId === ''
        ? null
        : userToggledDocId
      : isAutoPreview
        ? initialDocId
        : null

  const [previewPage, setPreviewPage] = useState(1)
  const { data: previewDoc, isLoading: previewLoading } = useDocument(previewDocId ?? undefined)

  useEffect(() => {
    onPreviewChange?.(Boolean(previewDocId))
  }, [previewDocId, onPreviewChange])

  const handleOpenSeePage = (docId: string) => {
    setUserToggledDocId(docId)
    setPreviewPage(1)
  }

  const act = (request: ResolveRequest) =>
    resolve.mutate({ itemId: item.itemId, request }, { onSuccess: (resolved) => onResolved(resolved) })

  // The primary action of each kind (docs/11 §6.5), named after what it does.
  const primary: { label: string; request: ResolveRequest; disabled?: boolean } | undefined =
    isMapping && allowed.has('CONFIRM_MAPPING') && mapping
      ? { label: t('mapping.confirm'), request: { action: 'CONFIRM_MAPPING', mapping }, disabled: !isComplete(mapping) }
      : item.kind === 'PROPOSED_MATCH' && allowed.has('CONFIRM_MATCH')
      ? { label: t('actions.CONFIRM_MATCH'), request: { action: 'CONFIRM_MATCH', matchId: item.subject.matchId } }
      : item.kind === 'UNMATCHED_DOCUMENT' && pickedLine && allowed.has('MATCH')
        ? {
            label: t('actions.MATCH', { date: formatDate(pickedLine.date) }),
            request: { action: 'MATCH', bankLineIds: [pickedLine.txId] },
          }
        : item.kind === 'POSSIBLE_DUPLICATE' && allowed.has('CONFIRM_DUPLICATE')
          ? { label: t('actions.CONFIRM_DUPLICATE'), request: { action: 'CONFIRM_DUPLICATE' } }
          : item.kind === 'LOW_CONFIDENCE_VALUE' && allowed.has('ACCEPT_AS_READ')
            ? { label: t('actions.ACCEPT_AS_READ'), request: { action: 'ACCEPT_AS_READ' } }
            : item.kind === 'UNMATCHED_BANK_LINE' && allowed.has('NO_DOCUMENT_NEEDED')
              ? { label: t('actions.NO_DOCUMENT_NEEDED'), request: { action: 'NO_DOCUMENT_NEEDED' } }
              : undefined
  const quiet = (['REJECT_MATCH', 'NOT_DUPLICATE', 'NOT_YET_PAID'] as const).filter((a) => allowed.has(a))
  // T009-03a: an invoice's or receipt's total or date, as printed; what was read is kept.
  const field = item.subject.field ?? ''
  const canCorrect = allowed.has('CORRECT_VALUE') && documents.length > 0 && Boolean(field)
  const busy = resolve.isPending
  useQueueKeys(
    useMemo(
      () => ({ primary: primary && !busy && !primary.disabled ? () => act(primary.request) : undefined, close: onClose }),
      // eslint-disable-next-line react-hooks/exhaustive-deps -- the action changes with the item and the choice
      [item.itemId, primary?.label, primary?.disabled, busy, onClose],
    ),
  )

  return (
    <div className={`review-split-layout ${previewDocId ? 'with-preview' : ''}`}>
      {previewDocId && (
        <aside
          className="review-split-preview"
          aria-label={t('panel.documentPreview', { defaultValue: 'Document preview' })}
        >
          <div className="review-preview-header">
            <span className="file flex items-center gap-2 font-medium text-xs truncate">
              <Icon name="file-text" size="sm" />
              <span className="truncate">{previewDoc?.fileName || t('panel.document')}</span>
            </span>
            <div className="row gap-2 items-center shrink-0">
              <Link
                to={`/documents/${previewDocId}`}
                target="_blank"
                rel="noopener noreferrer"
                className="link small flex items-center gap-1"
                title={t('panel.openDocument')}
              >
                <span>{t('panel.openDocument')}</span>
                <Icon name="external" size="sm" />
              </Link>
              <button
                type="button"
                className="icon-button icon-button-sm"
                aria-label={t('common:actions.close', { defaultValue: 'Close preview' })}
                onClick={() => setUserToggledDocId('')}
              >
                <Icon name="x" size="sm" />
              </button>
            </div>
          </div>
          <div className="flex-1 overflow-y-auto">
            {previewLoading ? (
              <p className="muted small p-4">{t('common:loading', { defaultValue: 'Loading...' })}</p>
            ) : previewDoc ? (
              <PageViewer
                docId={previewDoc.docId}
                fileName={previewDoc.fileName}
                pageCount={previewDoc.pageCount ?? previewDoc.pages?.length ?? 1}
                page={previewPage}
                onPage={setPreviewPage}
                witness={previewDoc.pages?.[previewPage - 1]?.witness}
              />
            ) : (
              <p className="muted small p-4">{t('panel.missing')}</p>
            )}
          </div>
        </aside>
      )}

      <section className="fix review-split-panel" aria-labelledby="fix-h">
        <div className="fix-head">
          <div className="pager-line">
            <span className="row">
              <span className="badge badge-brand">
                <Icon name={KIND_ICON[item.kind] ?? 'inbox'} size="sm" />
                {t(`kinds.${item.kind}`)}
              </span>
              {month && <span>{monthName(month)}</span>}
            </span>
            <span className="row">
              <span>{t('panel.position', { index: position.index + 1, total: position.total })}</span>
              <button type="button" className="icon-button" aria-label={t('panel.close')} onClick={onClose}>
                <Icon name="x" />
              </button>
            </span>
          </div>
          <h2 id="fix-h">{item.title}</h2>
          <p>{t(`why.${item.kind}`)}</p>
        </div>

        <div className="fix-body">
          {subjects.lines.map((line) => (
            <LineSubject
              key={line.txId}
              line={line}
              onSeePage={handleOpenSeePage}
              activePreviewDocId={previewDocId}
            />
          ))}
          {documents.map((record) => (
            <RecordSubject
              key={'invoiceId' in record ? record.invoiceId : record.receiptId}
              record={record}
              onSeePage={handleOpenSeePage}
              activePreviewDocId={previewDocId}
            />
          ))}
          {item.kind === 'POSSIBLE_DUPLICATE' &&
            (item.subject.docIds ?? []).map((docId, i) => (
              <DocumentSubject
                key={docId}
                docId={docId}
                label={i === 0 ? t('panel.thisCopy') : t('panel.earlier')}
                onSeePage={handleOpenSeePage}
                activePreviewDocId={previewDocId}
              />
            ))}
          {isMapping && mappingDocId && <DocumentSubject docId={mappingDocId} label={t('panel.document')} />}
          {isMapping &&
            (mappingLoading ? (
              <p className="muted small">{t('mapping.loading')}</p>
            ) : mappingView && mapping ? (
              <MappingEditor
                view={mappingView}
                value={mapping}
                onChange={setEdited}
                disabled={busy}
                badRows={(item.suggestion?.mapping as { badRows?: number[] } | undefined)?.badRows ?? []}
              />
            ) : (
              <p className="muted small">{t('mapping.unavailable')}</p>
            ))}
          {isMapping && mapping && !isComplete(mapping) && <p className="muted small">{t('mapping.incomplete')}</p>}
          {item.kind === 'PROPOSED_MATCH' && <Proposal item={item} />}
          {item.kind === 'UNMATCHED_DOCUMENT' && <LinePicker lines={candidates} picked={pickedLine?.txId} onPick={setPicked} />}

        {(quiet.length > 0 || allowed.has('IGNORE') || canCorrect) && (
          <div className="other-actions">
            {canCorrect && !correcting && (
              <Button variant="quiet" size="sm" onClick={() => setCorrecting(true)}>
                {t('actions.CORRECT_VALUE')}
              </Button>
            )}
            {quiet.map((action) => (
              <Button key={action} variant="quiet" size="sm" disabled={resolve.isPending} onClick={() => act({ action })}>
                {t(`actions.${action}`)}
              </Button>
            ))}
            {allowed.has('IGNORE') && !reasonOpen && (
              <Button variant="quiet" size="sm" onClick={() => setReasonOpen(true)}>
                {t('actions.IGNORE')}
              </Button>
            )}
          </div>
        )}
        {correcting && (
          <form
            className="field"
            onSubmit={(e) => {
              e.preventDefault()
              act({ action: 'CORRECT_VALUE', field, value: correction.trim() })
            }}
          >
            <label className="label" htmlFor="correct-value">
              {t('panel.correctLabel', { field: t(`fields.${field}`, { defaultValue: field }) })}
            </label>
            <input id="correct-value" className="input" value={correction} onChange={(e) => setCorrection(e.target.value)} />
            <p className="muted small">{t('panel.correctHint')}</p>
            <div className="row">
              <Button type="submit" size="sm" disabled={!correction.trim() || resolve.isPending}>
                {t('actions.saveCorrection')}
              </Button>
            </div>
          </form>
        )}
        {reasonOpen && (
          <form
            className="field"
            onSubmit={(e) => {
              e.preventDefault()
              act({ action: 'IGNORE', reason })
            }}
          >
            <label className="label" htmlFor="ignore-reason">
              {t('panel.reason')}
            </label>
            <textarea id="ignore-reason" className="textarea" value={reason} onChange={(e) => setReason(e.target.value)} />
            <p className="muted small">{t('panel.reasonHint')}</p>
            <div className="row">
              <Button type="submit" size="sm" disabled={!reason.trim() || resolve.isPending}>
                {t('actions.saveIgnore')}
              </Button>
            </div>
          </form>
        )}
      </div>

      <div className="fix-foot">
        {primary && (
          <Button disabled={resolve.isPending || primary.disabled} onClick={() => act(primary.request)}>
            <Icon name="check" size="sm" />
            <span>{primary.label}</span>
          </Button>
        )}
        <Button variant="secondary" onClick={onSkip}>
          {t('panel.skip')}
        </Button>
        <span className="keys hide-compact">
          <span>
            <span className="kbd">J</span> <span className="kbd">K</span> {t('panel.keys')}
          </span>
          <span>
            <span className="kbd">{t('panel.enterKey')}</span> {t('panel.keyEnter')}
          </span>
        </span>
      </div>
    </section>
  </div>
)
}
