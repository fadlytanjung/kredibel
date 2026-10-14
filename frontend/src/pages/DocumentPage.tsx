/**
 * DocumentPage: one document, its page viewer beside what was read from it (transactions or
 * records, a page at a time), its findings and its details.
 *
 * Normative references:
 * - spec 003 US-003-3 (AC-003-9) and US-003-4 (AC-003-10); spec 005 T005-11; spec 006
 * - docs/11 §6.3; mock design/mocks/document.html
 */

import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { type BankLine, isIncoming, lineBox, StatementLines, useBankLines } from '../entities/bank-line'
import { type Document, DOC_TYPE_BADGE, downloadOriginal, PageViewer, useDeleteDocument, useDocument } from '../entities/document'
import { FindingList, useDocumentFindings } from '../entities/finding'
import { InvoiceCard, ReceiptCard, useInvoices, useReceipts, type ValueFocus } from '../entities/record'
import { sumDecimals } from '../shared/lib/decimal'
import { formatDate } from '../shared/lib/formatDate'
import { formatMoney } from '../shared/lib/formatMoney'
import { Badge, Button, Icon } from '../shared/ui'

type Tab = 'records' | 'findings' | 'details'
type Money = { amount: string; currency: string } | null | undefined

const VERDICT = {
  CLEAN: { variant: 'clean', icon: 'shield-check' },
  SUSPICIOUS: { variant: 'high', icon: 'shield-alert' },
  TAMPERED: { variant: 'tampered', icon: 'shield-x' },
  UNVERIFIABLE: { variant: 'medium', icon: 'shield-alert' },
} as const

function money(value: Money): string {
  return value ? formatMoney(value.amount, { currency: value.currency }) : '—'
}

export function DocumentPage() {
  const { docId } = useParams<{ docId: string }>()
  const navigate = useNavigate()
  const { t } = useTranslation(['documents', 'common'])
  const { data: doc, isLoading } = useDocument(docId)
  const deleteMutation = useDeleteDocument()
  const read = Boolean(doc?.reading)
  const isStatement = read && doc?.docType === 'BANK_STATEMENT'
  const isInvoice = read && (doc?.docType === 'SALES_INVOICE' || doc?.docType === 'PURCHASE_INVOICE')
  const isReceipt = read && doc?.docType === 'RECEIPT'
  const { data: linePage, isLoading: linesLoading } = useBankLines(isStatement ? docId : undefined)
  const { data: invoicePage } = useInvoices(isInvoice ? docId : undefined)
  const { data: receiptPage } = useReceipts(isReceipt ? docId : undefined)
  const { data: findingPage } = useDocumentFindings(doc?.integrity ? docId : undefined)
  const [focus, setFocus] = useState<ValueFocus | null>(null)
  const [selectedPage, setSelectedPage] = useState<number>(1)
  const [tab, setTab] = useState<Tab | null>(null)
  const [showConfirmDelete, setShowConfirmDelete] = useState<boolean>(false)

  if (isLoading) {
    return (
      <div className="page">
        <p className="muted">{t('common:common.loading')}</p>
      </div>
    )
  }

  if (!doc) {
    return (
      <div className="page">
        <p className="muted">{t('documents:table.empty')}</p>
        <Link className="link" to="/documents">
          {t('documents:detail.back')}
        </Link>
      </div>
    )
  }

  const handleDelete = async () => {
    if (!docId) return
    await deleteMutation.mutateAsync(docId)
    navigate('/documents')
  }

  const pagesCount = doc.pageCount || doc.pages?.length || 0
  // One value at a time is lit on its page: a statement line's amount, an invoice or receipt
  // field, or a finding's evidence.
  const showValue = (value: ValueFocus) => {
    setFocus(value)
    setSelectedPage(value.page)
  }
  const selectLine = (line: BankLine) => {
    const bbox = lineBox(line)
    if (bbox && line.page) showValue({ key: line.txId, page: line.page, bbox })
    else if (line.page) setSelectedPage(line.page)
  }
  const highlight = focus && focus.page === selectedPage ? focus.bbox : undefined
  const lines = linePage?.items ?? []
  const findings = (findingPage?.items ?? []).filter((f) => f.status === 'OPEN' || f.status === 'ACKNOWLEDGED')
  const recordCount = isStatement
    ? lines.length
    : isInvoice
      ? (invoicePage?.items.length ?? 0)
      : (receiptPage?.items.length ?? 0)
  const tabs: Tab[] = [...(isStatement || isInvoice || isReceipt ? (['records'] as const) : []), 'findings', 'details']
  const active = tab && tabs.includes(tab) ? tab : tabs[0]
  const recordsLabel = isStatement ? 'transactions' : isInvoice ? 'invoices' : 'receipts'
  const tabLabel = { records: t(`documents:detail.tabs.${recordsLabel}`), findings: t('documents:detail.tabs.findings'), details: t('documents:detail.tabs.details') }
  const tabCount = { records: recordCount, findings: doc.integrity ? findings.length : undefined, details: undefined }

  const pane = (
    <section className="doc-pane" aria-label={t('documents:detail.pane')}>
      {isStatement && <StatementFigures doc={doc} lines={linesLoading ? undefined : lines} />}
      <div className="tabs" role="tablist" aria-label={t('documents:detail.tabs.label')}>
        {tabs.map((key) => (
          <button
            key={key}
            type="button"
            role="tab"
            id={`doc-tab-${key}`}
            aria-controls="doc-tabpanel"
            aria-selected={active === key}
            className="tab"
            onClick={() => setTab(key)}
          >
            {tabLabel[key]}
            {tabCount[key] !== undefined && (
              <span className={`count ${key === 'findings' && tabCount[key] ? 'is-attn' : ''}`}>{tabCount[key]}</span>
            )}
          </button>
        ))}
      </div>
      <div role="tabpanel" id="doc-tabpanel" aria-labelledby={`doc-tab-${active}`} className="stack gap-3">
        {active === 'records' && isStatement && (
          linesLoading ? (
            <p className="muted small">{t('documents:detail.loadingLines')}</p>
          ) : (
            <StatementLines lines={lines} selectedTxId={focus?.key} onSelect={selectLine} />
          )
        )}
        {active === 'records' && isInvoice && (
          <>
            {doc.reading && (
              <p className="small muted">
                {t('documents:detail.recordsSummary', {
                  agreed: doc.reading.fieldsAgreed ?? 0,
                  compared: doc.reading.fieldsCompared ?? 0,
                })}
              </p>
            )}
            {invoicePage?.items.map((inv) => (
              <InvoiceCard key={inv.invoiceId} record={inv} focused={focus?.key} onFocus={showValue} />
            ))}
          </>
        )}
        {active === 'records' &&
          isReceipt &&
          receiptPage?.items.map((rc) => (
            <ReceiptCard key={rc.receiptId} record={rc} focused={focus?.key} onFocus={showValue} />
          ))}
        {active === 'findings' &&
          (doc.integrity ? (
            <FindingList findings={findingPage?.items ?? []} focused={focus?.key} onFocus={showValue} />
          ) : (
            <p className="muted small">{t('documents:detail.checksAfterReading')}</p>
          ))}
        {active === 'details' && <DocumentDetails doc={doc} pagesCount={pagesCount} />}
      </div>
    </section>
  )

  return (
    <div className="page stack gap-5">
      <header className="stack gap-2">
        <h1 className="type-title">{doc.fileName}</h1>
        <p className="muted">{summary(doc, t)}</p>
        <div className="doc-status">
          {doc.docType && doc.docType !== 'UNKNOWN' && (
            <Badge variant={DOC_TYPE_BADGE[doc.docType]?.variant ?? 'outline'}>
              {t(`documents:detail.docType.${doc.docType}`, { defaultValue: doc.docType })}
            </Badge>
          )}
          <StatusBadge doc={doc} />
          {doc.integrity?.verdict && (
            <Badge variant={VERDICT[doc.integrity.verdict].variant}>
              <Icon name={VERDICT[doc.integrity.verdict].icon} size="sm" />
              {t(`documents:detail.verdictBadge.${doc.integrity.verdict}`)}
            </Badge>
          )}
          <span className="spacer" />
          <span className="row">
            <Button variant="secondary" size="sm" onClick={() => void downloadOriginal(doc.docId, doc.fileName)}>
              <Icon name="download" size="sm" />
              {t('documents:detail.downloadOriginal')}
            </Button>
            <Button variant="ghost" size="sm" onClick={() => setShowConfirmDelete(true)}>
              <Icon name="trash" size="sm" />
              {t('documents:detail.deleteDocument')}
            </Button>
          </span>
        </div>
      </header>

      {showConfirmDelete && (
        <div className="banner banner-critical" role="alert">
          <p>{t('documents:detail.confirmDelete', { name: doc.fileName })}</p>
          <div className="row gap-2 mt-2">
            <Button variant="secondary" size="sm" disabled={deleteMutation.isPending} onClick={() => void handleDelete()}>
              {t('documents:detail.confirm')}
            </Button>
            <Button variant="secondary" size="sm" onClick={() => setShowConfirmDelete(false)}>
              {t('documents:detail.cancel')}
            </Button>
          </div>
        </div>
      )}

      {doc.heldAsDuplicate && doc.duplicate && (
        <div className="found" role="status">
          <Icon name="copy" />
          <div className="stack gap-1">
            <strong>{t('documents:status.possibleCopy')}</strong>
            <p className="small">{t('documents:detail.possibleCopy')}</p>
            <Link className="link small" to={`/documents/${doc.duplicate.ofDocId}`}>
              {t('documents:detail.openEarlierCopy')}
            </Link>
          </div>
        </div>
      )}

      {pagesCount > 0 ? (
        <div className="doc-layout">
          <PageViewer
            docId={doc.docId}
            fileName={doc.fileName}
            pageCount={pagesCount}
            page={selectedPage}
            onPage={setSelectedPage}
            highlight={highlight}
            witness={doc.pages?.[selectedPage - 1]?.witness}
          />
          {pane}
        </div>
      ) : (
        pane
      )}
    </div>
  )
}

type T = ReturnType<typeof useTranslation>['t']

function summary(doc: Document, t: T): string {
  const type = t(`documents:detail.docType.${doc.docType ?? 'UNKNOWN'}`)
  const uploaded = formatDate(doc.uploadedAt)
  const meta = doc.statementMeta
  if (meta?.periodStart && meta.periodEnd) {
    const account = [meta.bankName, meta.accountMasked].filter(Boolean).join(' ')
    return t('documents:detail.summary.statement', {
      type,
      account,
      start: formatDate(meta.periodStart),
      end: formatDate(meta.periodEnd),
      uploaded,
    })
  }
  return t('documents:detail.summary.other', { type, uploaded })
}

function StatusBadge({ doc }: { doc: Document }) {
  const { t } = useTranslation('documents')
  if (doc.reading && (doc.reading.fieldsCompared ?? 0) > 0) {
    return (
      <Badge variant="brand">
        <Icon name="check" size="sm" />
        {t('detail.readBadge', { agreed: doc.reading.fieldsAgreed ?? 0, compared: doc.reading.fieldsCompared ?? 0 })}
      </Badge>
    )
  }
  if (doc.heldAsDuplicate) return <Badge variant="evidence">{t('status.possibleCopy')}</Badge>
  if (doc.status === 'FAILED') return <Badge variant="critical">{t('status.failed')}</Badge>
  if (doc.status === 'DUPLICATE') return <Badge variant="outline">{t('status.duplicate')}</Badge>
  if (doc.status === 'NEEDS_INPUT') return <Badge variant="medium">{t('status.needsInput')}</Badge>
  if (doc.status === 'DONE') return <Badge variant="brand">{t('status.done')}</Badge>
  return <Badge variant="outline">{t('status.reading')}</Badge>
}

/** Opening and closing as printed, and the lines' money in and out, added exactly. */
function StatementFigures({ doc, lines }: { doc: Document; lines?: BankLine[] }) {
  const { t } = useTranslation('documents')
  const meta = doc.statementMeta
  const currency = meta?.currency ?? lines?.[0]?.amount.currency ?? meta?.opening?.currency
  const credits = lines?.filter(isIncoming) ?? []
  const debits = lines?.filter((line) => !isIncoming(line)) ?? []
  const total = (items: BankLine[]) =>
    lines && currency ? formatMoney(sumDecimals(items.map((l) => l.amount.amount.replace(/^-/, ''))), { currency }) : '—'
  return (
    <dl className="ledger-figures">
      <div>
        <dt>{t('detail.opening')}</dt>
        <dd className="v">{money(meta?.opening)}</dd>
        {meta?.periodStart && <dd className="n">{t('detail.figures.asPrinted', { date: formatDate(meta.periodStart) })}</dd>}
      </div>
      <div>
        <dt>{t('detail.closing')}</dt>
        <dd className="v">{money(meta?.closing)}</dd>
        {meta?.periodEnd && <dd className="n">{t('detail.figures.asPrinted', { date: formatDate(meta.periodEnd) })}</dd>}
      </div>
      <div>
        <dt>{t('detail.figures.moneyIn')}</dt>
        <dd className="v">{total(credits)}</dd>
        {lines && <dd className="n">{t('detail.figures.credits', { count: credits.length })}</dd>}
      </div>
      <div>
        <dt>{t('detail.figures.moneyOut')}</dt>
        <dd className="v">{total(debits)}</dd>
        {lines && <dd className="n">{t('detail.figures.debits', { count: debits.length })}</dd>}
      </div>
    </dl>
  )
}

function DocumentDetails({ doc, pagesCount }: { doc: Document; pagesCount: number }) {
  const { t } = useTranslation('documents')
  const meta = doc.statementMeta
  const witness = doc.pages?.[0]?.witness
  const rows: [string, string][] = [[t('detail.info.type'), t(`detail.docType.${doc.docType ?? 'UNKNOWN'}`)]]
  if (meta) {
    rows.push(
      [t('detail.bank'), meta.bankName || '—'],
      [t('detail.account'), meta.accountMasked || '—'],
      [
        t('detail.period'),
        meta.periodStart && meta.periodEnd
          ? `${formatDate(meta.periodStart)} ${t('detail.to')} ${formatDate(meta.periodEnd)}`
          : '—',
      ],
      [t('detail.currency'), meta.currency || '—'],
    )
  }
  if (pagesCount > 0) {
    const kind = witness === 'TEXT_LAYER' ? t('detail.digital') : witness === 'OCR' ? t('detail.scanned') : ''
    rows.push([t('detail.info.pages'), kind ? `${pagesCount} · ${kind}` : String(pagesCount)])
  }
  if (doc.reading && (doc.reading.fieldsCompared ?? 0) > 0) {
    rows.push([
      t('detail.info.valuesFound'),
      t('detail.info.valuesFoundValue', { agreed: doc.reading.fieldsAgreed ?? 0, compared: doc.reading.fieldsCompared ?? 0 }),
    ])
  }
  if (doc.ledgerMeta) {
    rows.push([t('detail.rowsImported'), String(doc.ledgerMeta['rowsImported'] || doc.ledgerMeta['rows'] || '—')])
  }
  rows.push([t('detail.info.uploaded'), formatDate(doc.uploadedAt)])
  return (
    <div className="card p-4 stack gap-2">
      {rows.map(([label, value]) => (
        <div key={label} className="row spread">
          <span className="muted">{label}</span>
          <strong>{value}</strong>
        </div>
      ))}
    </div>
  )
}
