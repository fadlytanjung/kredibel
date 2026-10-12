/**
 * DocumentPage: Document detail view with page viewer, read values, findings, and deletion.
 *
 * Normative references:
 * - spec 003 US-003-3 (AC-003-9) and US-003-4 (AC-003-10)
 * - docs/11 §6
 */

import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { downloadOriginal, PageImage, useDeleteDocument, useDocument } from '../entities/document'
import { formatDate } from '../shared/lib/formatDate'
import { Badge, Button, Icon } from '../shared/ui'

export function DocumentPage() {
  const { docId } = useParams<{ docId: string }>()
  const navigate = useNavigate()
  const { t } = useTranslation(['documents', 'common'])
  const { data: doc, isLoading } = useDocument(docId)
  const deleteMutation = useDeleteDocument()

  const [selectedPage, setSelectedPage] = useState<number>(1)
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

  return (
    <div className="page stack gap-6">
      <div className="page-head">
        <div className="row items-center gap-2">
          <Link className="link small" to="/documents">
            &larr; {t('documents:detail.back')}
          </Link>
        </div>
        <div className="spread items-center">
          <div>
            <h1 className="type-title">{doc.fileName}</h1>
            <p className="muted small">
              {doc.docType} &middot; {formatDate(doc.uploadedAt)}
            </p>
          </div>
          <div className="row gap-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => void downloadOriginal(doc.docId, doc.fileName)}
            >
              <Icon name="download" size="sm" />
              {t('documents:detail.downloadOriginal')}
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setShowConfirmDelete(true)}
            >
              <Icon name="trash" size="sm" />
              {t('documents:detail.deleteDocument')}
            </Button>
          </div>
        </div>
      </div>

      {showConfirmDelete && (
        <div className="banner banner-critical" role="alert">
          <p>{t('documents:detail.confirmDelete', { name: doc.fileName })}</p>
          <div className="row gap-2 mt-2">
            <Button
              variant="secondary"
              size="sm"
              disabled={deleteMutation.isPending}
              onClick={() => void handleDelete()}
            >
              {t('documents:detail.confirm')}
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setShowConfirmDelete(false)}
            >
              {t('documents:detail.cancel')}
            </Button>
          </div>
        </div>
      )}

      {/* Pages & Viewer */}
      {pagesCount > 0 && (
        <section className="stack gap-4">
          <h2 className="type-h2">{t('documents:detail.pages')} ({pagesCount})</h2>
          <div className="row gap-4 items-start flex-wrap">
            {/* Thumbnails strip */}
            <div
              className="stack gap-2 shrink-0 overflow-y-auto"
              style={{ width: '140px', maxHeight: '500px' }} /* allow-raw-style: thumbnail strip viewport */
            >
              {Array.from({ length: pagesCount }, (_, i) => i + 1).map((pNo) => (
                <button
                  key={pNo}
                  type="button"
                  onClick={() => setSelectedPage(pNo)}
                  className={`card p-2 text-left cursor-pointer ${selectedPage === pNo ? 'border-brand' : ''}`}
                >
                  <PageImage
                    docId={doc.docId}
                    pageNo={pNo}
                    variant="thumb"
                    alt={t('documents:detail.page', { page: pNo })}
                    className="w-full h-auto block"
                  />
                  <span className="small muted block text-center mt-1">
                    {t('documents:detail.page', { page: pNo })}
                  </span>
                </button>
              ))}
            </div>

            {/* Selected Page Full Viewer */}
            <div
              className="card p-4 stack gap-2 flex-1 justify-center"
              style={{ minWidth: '280px' }} /* allow-raw-style: page viewer minimum width */
            >
              <div className="spread items-center">
                <span className="font-medium">
                  {t('documents:detail.page', { page: selectedPage })}
                </span>
                {doc.pages?.[selectedPage - 1] && (
                  <Badge variant="outline">
                    {doc.pages[selectedPage - 1].witness === 'TEXT_LAYER'
                      ? t('documents:detail.digital')
                      : t('documents:detail.scanned')}
                  </Badge>
                )}
              </div>
              <div className="overflow-auto text-center" style={{ maxHeight: '650px' }} /* allow-raw-style: viewer max viewport height */>
                <PageImage
                  docId={doc.docId}
                  pageNo={selectedPage}
                  variant="full"
                  alt={t('documents:detail.page', { page: selectedPage })}
                  className="max-w-full h-auto m-auto"
                />
              </div>
            </div>
          </div>
        </section>
      )}

      {/* Extracted values */}
      <section className="stack gap-3">
        <h2 className="type-h2">{t('documents:detail.extractedValues')}</h2>
        {doc.statementMeta && (
          <div className="card p-4 stack gap-2">
            <div className="row spread">
              <span className="muted">{t('documents:detail.bank')}</span>
              <strong>{String(doc.statementMeta['bankName'] || '—')}</strong>
            </div>
            <div className="row spread">
              <span className="muted">{t('documents:detail.account')}</span>
              <strong>{String(doc.statementMeta['accountMasked'] || '—')}</strong>
            </div>
            <div className="row spread">
              <span className="muted">{t('documents:detail.period')}</span>
              <strong>
                {String(doc.statementMeta['periodStart'] || '—')} {t('documents:detail.to')}{' '}
                {String(doc.statementMeta['periodEnd'] || '—')}
              </strong>
            </div>
          </div>
        )}
        {doc.ledgerMeta && (
          <div className="card p-4 stack gap-2">
            <div className="row spread">
              <span className="muted">{t('documents:detail.rowsImported')}</span>
              <strong>{String(doc.ledgerMeta['rowsImported'] || doc.ledgerMeta['rows'] || '—')}</strong>
            </div>
          </div>
        )}
        {!doc.statementMeta && !doc.ledgerMeta && (
          <p className="muted small">{t('documents:status.reading')}</p>
        )}
      </section>

      {/* Findings */}
      <section className="stack gap-3">
        <h2 className="type-h2">{t('documents:detail.findings')}</h2>
        {doc.integrity?.verdict ? (
          <div className="row items-center gap-2">
            <Badge
              variant={
                doc.integrity.verdict === 'CLEAN'
                  ? 'clean'
                  : doc.integrity.verdict === 'TAMPERED'
                  ? 'tampered'
                  : 'critical'
              }
            >
              {doc.integrity.verdict}
            </Badge>
          </div>
        ) : (
          <p className="muted small">{t('documents:detail.noFindings')}</p>
        )}
      </section>
    </div>
  )
}
