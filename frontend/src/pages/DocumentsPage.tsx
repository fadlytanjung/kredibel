/**
 * DocumentsPage: Documents library with live status, filters, and upload tray.
 *
 * Normative references:
 * - spec 003 US-003-3 (AC-003-7, AC-003-8)
 * - docs/11 §5a (responsive table)
 * - tools/design/mocks/screens.py documents()
 */

import { useContext } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router-dom'
import { useDocuments, useDocumentsLive, type DocType, type Document } from '../entities/document'
import { AuthContext } from '../entities/session'
import { UploadSheet } from '../features/upload'
import { formatDate, formatMonth } from '../shared/lib/formatDate'
import { Badge, DataTable, type DataTableColumn, type DataTableFilter, Icon, type IconName } from '../shared/ui'

function _docIcon(doc: Document): IconName {
  if (doc.status === 'DUPLICATE') return 'copy'
  if (doc.docType === 'LEDGER_EXPORT') return 'table'
  if (doc.docType === 'RECEIPT') return 'receipt'
  return 'file-text'
}

const DOC_TYPE_BADGE: Record<string, { variant: 'brand' | 'clean' | 'evidence' | 'low' | 'outline' | 'default' }> = {
  BANK_STATEMENT: { variant: 'brand' },
  SALES_INVOICE: { variant: 'clean' },
  PURCHASE_INVOICE: { variant: 'evidence' },
  RECEIPT: { variant: 'low' },
  LEDGER_EXPORT: { variant: 'outline' },
}

function _docSubtitle(doc: Document, t: (key: string, opts?: Record<string, unknown>) => string): string {
  const parts: string[] = []
  if (doc.docType && doc.docType !== 'UNKNOWN') {
    parts.push(t(`documents:detail.docType.${doc.docType}`, { defaultValue: doc.docType }))
  }
  if (doc.pageCount && doc.pageCount > 0) {
    parts.push(t('documents:table.pages', { count: doc.pageCount }))
  }
  return parts.join(' \u00b7 ') || t('documents:status.uploaded')
}

const PROCESSING = ['UPLOADED', 'SCREENING', 'READING', 'CHECKING']

export function DocumentsPage() {
  const { t } = useTranslation(['documents', 'common'])
  const auth = useContext(AuthContext)
  const navigate = useNavigate()

  // Every document of the workspace, newest first; the table filters, searches and pages them.
  const { data, isLoading: isRestLoading } = useDocuments({ limit: 200 })
  const live = useDocumentsLive(auth?.me?.orgId)
  const documents =
    auth?.me?.orgId && (live.documents.length > 0 || (!isRestLoading && !data?.items?.length))
      ? live.documents
      : (data?.items ?? [])
  const isLoading = live.loading && isRestLoading && documents.length === 0

  const of = (type: DocType) => (doc: Document) => doc.docType === type
  const filterDefs: { key: string; label: string; predicate: (doc: Document) => boolean }[] = [
    { key: 'ALL', label: t('documents:filters.all'), predicate: () => true },
    { key: 'STATEMENTS', label: t('documents:filters.statements'), predicate: of('BANK_STATEMENT') },
    { key: 'SALES', label: t('documents:filters.salesInvoices'), predicate: of('SALES_INVOICE') },
    { key: 'PURCHASE', label: t('documents:filters.purchaseInvoices'), predicate: of('PURCHASE_INVOICE') },
    { key: 'RECEIPTS', label: t('documents:filters.receipts'), predicate: of('RECEIPT') },
    { key: 'LEDGER', label: t('documents:filters.ledger'), predicate: of('LEDGER_EXPORT') },
    { key: 'DUPLICATES', label: t('documents:filters.duplicates'), predicate: (doc) => Boolean(doc.heldAsDuplicate) },
  ]
  const filters: DataTableFilter<Document>[] = filterDefs.map((f) => ({ ...f, count: documents.filter(f.predicate).length }))

  const statusOf = (doc: Document) => {
    if (doc.heldAsDuplicate) return t('documents:status.possibleCopy')
    if (doc.status === 'READING' && doc.pages && doc.pages.length > 0) {
      const donePages = doc.pages.filter((p) => p.status === 'DONE').length
      return t('documents:upload.readingPage', { page: donePages + 1, total: doc.pageCount })
    }
    return t(`documents:status.${doc.status.toLowerCase()}`, { defaultValue: doc.status })
  }
  const statusLine = (doc: Document) => (
    <span className="status-line">
      <Icon name={PROCESSING.includes(doc.status) ? 'refresh' : doc.status === 'DUPLICATE' ? 'copy' : 'check-circle'} size="sm" />
      {statusOf(doc)}
    </span>
  )
  const checkOf = (doc: Document) => {
    if (doc.docType === 'LEDGER_EXPORT') return <span className="muted small">{t('documents:status.noPages')}</span>
    const verdict = doc.integrity?.verdict
    if (verdict === 'CLEAN')
      return <Badge variant="clean" icon={<Icon name="shield-check" size="sm" />}>{t('documents:verdict.clean')}</Badge>
    if (verdict === 'TAMPERED')
      return <Badge variant="tampered" icon={<Icon name="shield-x" size="sm" />}>{t('documents:verdict.tampered')}</Badge>
    if (verdict === 'SUSPICIOUS')
      return <Badge variant="critical" icon={<Icon name="shield-alert" size="sm" />}>{t('documents:verdict.suspicious')}</Badge>
    if (verdict === 'UNVERIFIABLE') return <Badge variant="medium">{t('documents:verdict.unverifiable')}</Badge>
    if (PROCESSING.includes(doc.status)) return <span className="muted small">{t('documents:status.afterReading')}</span>
    // An exact copy is never read or checked; anything else without a verdict was not checked.
    if (doc.status === 'DUPLICATE') return <span className="muted small">{t('documents:status.copyNotChecked')}</span>
    return <span className="muted small">{t('documents:status.notChecked')}</span>
  }
  const riskOf = (doc: Document) =>
    doc.risk?.level ? (
      <Badge variant={doc.risk.level.toLowerCase() as 'critical' | 'high' | 'medium' | 'low'}>{doc.risk.level}</Badge>
    ) : (
      <span className="muted small">{t('documents:status.notYet')}</span>
    )

  const columns: DataTableColumn<Document>[] = [
    {
      key: 'document',
      header: t('documents:table.document'),
      sortable: true,
      sortValue: (doc) => doc.fileName.toLowerCase(),
      render: (doc) => (
        <span className="doc-cell">
          <span className={`thumb ${doc.docType === 'LEDGER_EXPORT' ? 'is-sheet' : ''}`}>
            <Icon name={_docIcon(doc)} />
          </span>
          <span>
            <Link className="doc-link" to={`/documents/${doc.docId}`} onClick={(e) => e.stopPropagation()}>
              <strong>{doc.fileName}</strong>
            </Link>
            <div className="row gap-2 items-center flex-wrap mt-1">
              {doc.docType && doc.docType !== 'UNKNOWN' && (
                <Badge variant={DOC_TYPE_BADGE[doc.docType]?.variant ?? 'outline'}>
                  {t(`documents:detail.docType.${doc.docType}`, { defaultValue: doc.docType })}
                </Badge>
              )}
              {doc.pageCount && doc.pageCount > 0 ? (
                <span className="muted small">{t('documents:table.pages', { count: doc.pageCount })}</span>
              ) : null}
            </div>
          </span>
        </span>
      ),
    },
    {
      key: 'summary',
      header: '',
      align: 'right',
      className: 'only-rt',
      wideOnMobile: true,
      render: (doc) => (
        <>
          {riskOf(doc)}
          {statusLine(doc)}
        </>
      ),
    },
    { key: 'status', header: t('documents:table.status'), hideOnMobile: true, sortable: true, sortValue: statusOf, render: statusLine },
    { key: 'check', header: t('documents:table.check'), hideOnMobile: true, render: checkOf },
    {
      key: 'risk',
      header: t('documents:table.risk'),
      hideOnMobile: true,
      sortable: true,
      sortValue: (doc) => ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'].indexOf(doc.risk?.level ?? ''),
      render: riskOf,
    },
    {
      key: 'months',
      header: t('documents:table.months'),
      hideOnMobile: true,
      sortable: true,
      sortValue: (doc) => doc.months?.[0] ?? '',
      render: (doc) => (doc.months?.length ? doc.months.map((m) => formatMonth(m, 'short') + ' ' + m.slice(0, 4)).join(', ') : '\u2014'),
    },
    {
      key: 'uploaded',
      header: t('documents:table.uploaded'),
      align: 'right',
      hideOnMobile: true,
      sortable: true,
      sortValue: (doc) => String(doc.uploadedAt ?? ''),
      render: (doc) => formatDate(doc.uploadedAt),
    },
  ]

  return (
    <div className="page">
      <div className="page-head">
        <h1 className="type-title">{t('documents:title')}</h1>
        <p>{t('documents:subtitle')}</p>
      </div>

      <div className="stack gap-6">
        <UploadSheet />
        <DataTable
          data={documents}
          columns={columns}
          getRowKey={(doc) => doc.docId}
          filters={filters}
          filterGroupAriaLabel={t('documents:filters.label')}
          searchable
          searchPlaceholder={t('documents:table.search')}
          searchPredicate={(doc, q) =>
            [doc.fileName, _docSubtitle(doc, t), statusOf(doc), ...(doc.months ?? [])].some((text) =>
              String(text).toLowerCase().includes(q),
            )
          }
          isLoading={isLoading}
          emptyMessage={<p className="muted">{t('documents:table.empty')}</p>}
          onRowClick={(doc) => navigate(`/documents/${doc.docId}`)}
        />
      </div>
    </div>
  )
}
