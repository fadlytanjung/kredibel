/**
 * The fix panel of one review item (spec 009, T009-05, AC-009-4, AC-009-5; docs/11 §6.5): what is
 * wrong, the subject with a link to its page, the suggestion, and only the actions its kind allows.
 */

import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { type BankLine, CASHFLOW_BADGE, useMonthBankLines } from '../../entities/bank-line'
import { useDocument } from '../../entities/document'
import { type Invoice, type Receipt, useMonthInvoices, useMonthReceipts } from '../../entities/record'
import { type ResolveRequest, type ReviewItem, useResolveReviewItem } from '../../entities/review'
import { formatDate } from '../../shared/lib/formatDate'
import { formatAmount } from '../../shared/lib/formatMoney'
import { Badge, Button, Icon } from '../../shared/ui'
import { KIND_ICON, monthName } from './kinds'
import { linesThatCouldPay, subjectsOf } from './subjects'
import { useQueueKeys } from './useQueueKeys'

export interface ItemPanelProps {
  item: ReviewItem
  position: { index: number; total: number }
  onResolved: (item: ReviewItem) => void
  onSkip: () => void
  onClose: () => void
}

function signed(line: BankLine) {
  const amount = Number(line.amount.amount)
  return `${amount > 0 ? '+' : ''}${formatAmount(line.amount.amount, { currency: line.amount.currency })}`
}

function LineSubject({ line }: { line: BankLine }) {
  const { t } = useTranslation(['review', 'months'])
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
        <Link className="citation" to={`/documents/${line.docId}`}>
          <Icon name="eye" size="sm" />
          {t('review:panel.seePage')}
        </Link>
      </div>
    </div>
  )
}

function RecordSubject({ record }: { record: Invoice | Receipt }) {
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
        <Link className="citation" to={`/documents/${record.docId}`}>
          <Icon name="eye" size="sm" />
          {t('review:panel.seePage')}
        </Link>
      </div>
    </div>
  )
}

function DocumentSubject({ docId, label }: { docId: string; label: string }) {
  const { t } = useTranslation('review')
  const { data: doc } = useDocument(docId)
  return (
    <div className="subject">
      <span className="ico">
        <Icon name="files" />
      </span>
      <span className="t">{doc?.fileName ?? docId}</span>
      <span className="s">
        {label}{' '}
        <Link className="citation" to={`/documents/${docId}`}>
          <Icon name="eye" size="sm" />
          {t('panel.openDocument')}
        </Link>
      </span>
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

export function ItemPanel({ item, position, onResolved, onSkip, onClose }: ItemPanelProps) {
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

  const monthLines = lineData?.items ?? []
  const subjects = subjectsOf(item, {
    lines: monthLines,
    invoices: invoiceData?.items ?? [],
    receipts: receiptData?.items ?? [],
  })
  const documents = [...subjects.invoices, ...subjects.receipts]
  const candidates = item.kind === 'UNMATCHED_DOCUMENT' && documents[0] ? linesThatCouldPay(documents[0], monthLines) : []
  const allowed = new Set(item.allowedActions)
  const pickedLine = candidates.find((l) => l.txId === picked) ?? candidates[0]

  const act = (request: ResolveRequest) =>
    resolve.mutate({ itemId: item.itemId, request }, { onSuccess: (resolved) => onResolved(resolved) })

  // The primary action of each kind (docs/11 §6.5), named after what it does.
  const primary: { label: string; request: ResolveRequest } | undefined =
    item.kind === 'PROPOSED_MATCH' && allowed.has('CONFIRM_MATCH')
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
      () => ({ primary: primary && !busy ? () => act(primary.request) : undefined, close: onClose }),
      // eslint-disable-next-line react-hooks/exhaustive-deps -- the action changes with the item and the choice
      [item.itemId, primary?.label, busy, onClose],
    ),
  )

  return (
    <section className="fix" aria-labelledby="fix-h">
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
          <LineSubject key={line.txId} line={line} />
        ))}
        {documents.map((record) => (
          <RecordSubject key={'invoiceId' in record ? record.invoiceId : record.receiptId} record={record} />
        ))}
        {item.kind === 'POSSIBLE_DUPLICATE' &&
          (item.subject.docIds ?? []).map((docId, i) => (
            <DocumentSubject key={docId} docId={docId} label={i === 0 ? t('panel.thisCopy') : t('panel.earlier')} />
          ))}
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
          <Button disabled={resolve.isPending} onClick={() => act(primary.request)}>
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
  )
}
