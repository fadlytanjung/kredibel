/**
 * DocumentsPage: Documents library with live status, filters, and upload tray.
 *
 * Normative references:
 * - spec 003 US-003-3 (AC-003-7, AC-003-8)
 * - docs/11 §5a (responsive table)
 * - tools/design/mocks/screens.py documents()
 */

import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { useDocuments, type DocType, type Document } from '../entities/document'
import { UploadSheet } from '../features/upload'
import { formatDate } from '../shared/lib/formatDate'
import { Badge, Icon, type IconName } from '../shared/ui'

type FilterKey = 'ALL' | 'STATEMENTS' | 'SALES' | 'PURCHASE' | 'RECEIPTS' | 'LEDGER' | 'DUPLICATES'

function _docIcon(doc: Document): IconName {
  if (doc.status === 'DUPLICATE') return 'copy'
  if (doc.docType === 'LEDGER_EXPORT') return 'table'
  if (doc.docType === 'RECEIPT') return 'receipt'
  return 'file-text'
}

function _docSubtitle(doc: Document, t: (key: string, opts?: Record<string, unknown>) => string): string {
  const parts: string[] = []
  if (doc.docType && doc.docType !== 'UNKNOWN') {
    parts.push(t(`documents:filters.${doc.docType.toLowerCase()}`, { defaultValue: doc.docType }))
  }
  if (doc.pageCount && doc.pageCount > 0) {
    parts.push(t('documents:table.pages', { count: doc.pageCount }))
  }
  return parts.join(' \u00b7 ') || t('documents:status.uploaded')
}

export function DocumentsPage() {
  const { t } = useTranslation(['documents', 'common'])
  const [activeFilter, setActiveFilter] = useState<FilterKey>('ALL')

  let filterArg: { type?: DocType; duplicate?: boolean } | undefined
  if (activeFilter === 'STATEMENTS') filterArg = { type: 'BANK_STATEMENT' }
  else if (activeFilter === 'SALES') filterArg = { type: 'SALES_INVOICE' }
  else if (activeFilter === 'PURCHASE') filterArg = { type: 'PURCHASE_INVOICE' }
  else if (activeFilter === 'RECEIPTS') filterArg = { type: 'RECEIPT' }
  else if (activeFilter === 'LEDGER') filterArg = { type: 'LEDGER_EXPORT' }
  else if (activeFilter === 'DUPLICATES') filterArg = { duplicate: true }

  const { data, isLoading } = useDocuments(filterArg)
  const documents = data?.items || []

  const chips: { key: FilterKey; label: string }[] = [
    { key: 'ALL', label: t('documents:filters.all') },
    { key: 'STATEMENTS', label: t('documents:filters.statements') },
    { key: 'SALES', label: t('documents:filters.salesInvoices') },
    { key: 'PURCHASE', label: t('documents:filters.purchaseInvoices') },
    { key: 'RECEIPTS', label: t('documents:filters.receipts') },
    { key: 'LEDGER', label: t('documents:filters.ledger') },
    { key: 'DUPLICATES', label: t('documents:filters.duplicates') },
  ]

  return (
    <div className="page">
      <div className="page-head">
        <h1 className="type-title">{t('documents:title')}</h1>
        <p>{t('documents:subtitle')}</p>
      </div>

      <div className="stack gap-6">
        <UploadSheet />

        <div className="stack gap-3">
          <div className="spread">
            <div className="chips" role="group" aria-label={t('documents:filters.all')}>
              {chips.map(({ key, label }) => {
                const isSelected = activeFilter === key
                return (
                  <button
                    key={key}
                    type="button"
                    className="chip"
                    aria-pressed={isSelected}
                    onClick={() => setActiveFilter(key)}
                  >
                    {label}
                  </button>
                )
              })}
            </div>
          </div>

          <div className="table-panel rt-wrap">
            <table className="data-table rt">
              <thead>
                <tr>
                  <th>{t('documents:table.document')}</th>
                  <th className="only-rt" aria-hidden="true" />
                  <th>{t('documents:table.status')}</th>
                  <th>{t('documents:table.check')}</th>
                  <th>{t('documents:table.risk')}</th>
                  <th>{t('documents:table.months')}</th>
                  <th className="r">{t('documents:table.uploaded')}</th>
                </tr>
              </thead>
              <tbody>
                {documents.length === 0 && !isLoading && (
                  <tr>
                    <td colSpan={7} className="muted text-center p-8">
                      {t('documents:table.empty')}
                    </td>
                  </tr>
                )}

                {documents.map((doc) => {
                  const iconName = _docIcon(doc)
                  const isProcessing = ['UPLOADED', 'SCREENING', 'READING', 'CHECKING'].includes(doc.status)
                  const isDuplicate = doc.status === 'DUPLICATE'

                  let statusText = t(`documents:status.${doc.status.toLowerCase()}`, { defaultValue: doc.status })
                  if (doc.heldAsDuplicate) statusText = t('documents:status.possibleCopy')
                  if (doc.status === 'READING' && doc.pages && doc.pages.length > 0) {
                    const donePages = doc.pages.filter((p) => p.status === 'DONE').length
                    statusText = t('documents:upload.readingPage', { page: donePages + 1, total: doc.pageCount })
                  }

                  let checkBadge = <span className="muted small">{t('documents:status.screening')}</span>
                  if (doc.docType === 'LEDGER_EXPORT') {
                    checkBadge = <span className="muted small">{t('documents:status.noPages')}</span>
                  } else if (doc.integrity?.verdict) {
                    const verdict = doc.integrity.verdict
                    if (verdict === 'CLEAN') {
                      checkBadge = (
                        <Badge variant="clean" icon={<Icon name="shield-check" size="sm" />}>
                          {t('documents:verdict.clean')}
                        </Badge>
                      )
                    } else if (verdict === 'TAMPERED') {
                      checkBadge = (
                        <Badge variant="tampered" icon={<Icon name="shield-x" size="sm" />}>
                          {t('documents:verdict.tampered')}
                        </Badge>
                      )
                    } else if (verdict === 'SUSPICIOUS') {
                      checkBadge = (
                        <Badge variant="critical" icon={<Icon name="shield-alert" size="sm" />}>
                          {t('documents:verdict.suspicious')}
                        </Badge>
                      )
                    } else if (verdict === 'UNVERIFIABLE') {
                      checkBadge = <Badge variant="medium">{t('documents:verdict.unverifiable')}</Badge>
                    }
                  } else if (isProcessing) {
                    checkBadge = <span className="muted small">{t('documents:status.afterReading')}</span>
                  }

                  let riskBadge = <span className="muted small">{t('documents:status.notYet')}</span>
                  if (doc.risk?.level) {
                    const lvl = doc.risk.level.toLowerCase() as 'critical' | 'high' | 'medium' | 'low'
                    riskBadge = <Badge variant={lvl}>{doc.risk.level}</Badge>
                  }

                  const when = formatDate(doc.uploadedAt)

                  const monthsStr = doc.months && doc.months.length > 0 ? doc.months.join(', ') : '\u2014'

                  return (
                    <tr key={doc.docId}>
                      <td>
                        <span className="doc-cell">
                          <span className={`thumb ${doc.docType === 'LEDGER_EXPORT' ? 'is-sheet' : ''}`}>
                            <Icon name={iconName} />
                          </span>
                          <span>
                            <Link className="doc-link" to={`/documents/${doc.docId}`}>
                              <strong>{doc.fileName}</strong>
                            </Link>
                            <span className="sub">{_docSubtitle(doc, t)}</span>
                          </span>
                        </span>
                      </td>

                      <td className="r only-rt" data-cell="wide">
                        {riskBadge}
                        <span className="status-line">
                          <Icon name={isProcessing ? 'refresh' : isDuplicate ? 'copy' : 'check-circle'} size="sm" />
                          {statusText}
                        </span>
                      </td>

                      <td className="hide-rt" data-cell="hide">
                        <span className="status-line">
                          <Icon name={isProcessing ? 'refresh' : isDuplicate ? 'copy' : 'check-circle'} size="sm" />
                          {statusText}
                        </span>
                      </td>

                      <td className="hide-rt" data-cell="hide">
                        {checkBadge}
                      </td>

                      <td className="hide-rt" data-cell="hide">
                        {riskBadge}
                      </td>

                      <td className="hide-rt" data-cell="hide">
                        {monthsStr}
                      </td>

                      <td className="r hide-rt" data-cell="hide">
                        {when}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}
