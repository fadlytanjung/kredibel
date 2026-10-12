/**
 * MonthsPage: Month reconciliation overview and ADR-025 evidence prototypes.
 *
 * Normative references:
 * - spec 007 US-007-4 (AC-007-12) & US-007-5 (AC-007-14..19); ADR-025
 * - mocks design/mocks/reconciliation.html and design/mocks/month.html
 */

import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { useMonths } from '../entities/month'
import { useWorkspace } from '../entities/workspace'
import { Badge, Button, Icon } from '../shared/ui'

type TabValue = 'all' | 'bank' | 'documents' | 'currency'

export function MonthsPage() {
  const { t } = useTranslation(['months', 'common'])
  const { data: monthsData, isLoading } = useMonths()
  const { data: ws } = useWorkspace(true)
  const [tab, setTab] = useState<TabValue>('all')
  const [feedback, setFeedback] = useState<string | null>(null)

  const months = monthsData?.items ?? []
  const currency = ws?.currency ?? 'IDR'

  return (
    <div className="page stack gap-6">
      <header className="stack gap-2">
        <h1 className="type-title">{t('months:title')}</h1>
        <p className="muted">{t('months:subtitle')}</p>
        <p className="muted">{t('months:workspaceCurrency', { currency })}</p>
      </header>

      <div className="seg seg-touch" role="group" aria-label={t('months:viewsAria')}>
        <button
          type="button"
          aria-pressed={tab === 'all'}
          onClick={() => {
            setTab('all')
            setFeedback(null)
          }}
        >
          {t('months:tabs.all')}
        </button>
        <button
          type="button"
          aria-pressed={tab === 'bank'}
          onClick={() => {
            setTab('bank')
            setFeedback(null)
          }}
        >
          {t('months:tabs.bank')}
        </button>
        <button
          type="button"
          aria-pressed={tab === 'documents'}
          onClick={() => {
            setTab('documents')
            setFeedback(null)
          }}
        >
          {t('months:tabs.documents')}
        </button>
        <button
          type="button"
          aria-pressed={tab === 'currency'}
          onClick={() => {
            setTab('currency')
            setFeedback(null)
          }}
        >
          {t('months:tabs.currency')}
        </button>
      </div>

      {feedback && (
        <p className="muted" role="status">
          {feedback}
        </p>
      )}

      {tab === 'all' && (
        <section className="stack gap-4" aria-labelledby="all-months-h">
          <h2 className="type-h2" id="all-months-h">
            {t('months:all.title')}
          </h2>
          {isLoading ? (
            <p className="muted">{t('months:all.loading')}</p>
          ) : months.length === 0 ? (
            <div className="empty-state stack gap-3">
              <p className="muted">{t('months:all.empty')}</p>
              <Link to="/documents?upload=1" className="button button-primary">
                {t('months:all.uploadDocuments')}
              </Link>
            </div>
          ) : (
            <div className="table-panel rt-wrap">
              <table className="data-table rt">
                <thead>
                  <tr>
                    <th>{t('months:all.colMonth')}</th>
                    <th>{t('months:all.colStatus')}</th>
                    <th>{t('months:all.colStatements')}</th>
                    <th className="r">{t('months:all.colAction')}</th>
                  </tr>
                </thead>
                <tbody>
                  {months.map((m) => {
                    const isReconciled = m.state === 'RECONCILED'
                    const isNeedsReview = m.state === 'NEEDS_REVIEW'
                    return (
                      <tr key={m.month}>
                        <td>
                          <strong>{m.month}</strong>
                          {m.note && <div className="reason">{m.note}</div>}
                        </td>
                        <td>
                          <Badge
                            variant={isReconciled ? 'clean' : isNeedsReview ? 'medium' : 'default'}
                          >
                            {m.state}
                          </Badge>
                        </td>
                        <td>{t('months:all.statementsCount', { count: m.statements?.length ?? 0 })}</td>
                        <td className="r">
                          <Link
                            to={`/months/${encodeURIComponent(m.month)}`}
                            className="button button-secondary button-sm"
                          >
                            {t('months:all.viewDetails')}
                          </Link>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}

      {tab === 'bank' && (
        <section className="stack gap-4" aria-labelledby="bank-evidence-h">
          <h2 className="type-h2" id="bank-evidence-h">
            {t('months:bankEvidence.title')}
          </h2>
          <p>{t('months:bankEvidence.description')}</p>
          <div className="table-panel rt-wrap">
            <table className="data-table rt">
              <thead>
                <tr>
                  <th>{t('months:bankEvidence.colEvidence')}</th>
                  <th className="r">{t('months:bankEvidence.colAmount', { currency })}</th>
                  <th>{t('months:bankEvidence.colSupport')}</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>
                    <strong>{t('months:bankEvidence.daybreakCafe')}</strong>
                    <div className="reason">{t('months:bankEvidence.daybreakDate')}</div>
                    <span className="badge badge-outline">
                      <Icon name="building" size="sm" />
                      {t('months:bankEvidence.bankRecorded')}
                    </span>
                  </td>
                  <td className="r num">{t('months:bankEvidence.daybreakAmount')}</td>
                  <td data-cell="wide">
                    <span className="match-chip auto">
                      <Icon name="link" size="sm" />
                      <span>{t('months:bankEvidence.matchedTwoInvoices')}</span>
                    </span>
                    <p className="reason">{t('months:bankEvidence.inv101Detail', { currency })}</p>
                    <p className="reason">{t('months:bankEvidence.sameClientDetail')}</p>
                  </td>
                </tr>
                <tr>
                  <td>
                    <strong>{t('months:bankEvidence.harborview')}</strong>
                    <div className="reason">{t('months:bankEvidence.harborviewDate')}</div>
                    <span className="badge badge-outline">
                      <Icon name="building" size="sm" />
                      {t('months:bankEvidence.bankRecorded')}
                    </span>
                  </td>
                  <td className="r num">{t('months:bankEvidence.harborviewAmount')}</td>
                  <td data-cell="wide">
                    <span className="match-chip auto">
                      <Icon name="link" size="sm" />
                      <span>{t('months:bankEvidence.paidTwoTransfers')}</span>
                    </span>
                    <p className="reason">{t('months:bankEvidence.inv103Detail', { currency })}</p>
                    <p className="reason">{t('months:bankEvidence.inv103Balance', { currency })}</p>
                  </td>
                </tr>
                <tr>
                  <td>
                    <strong>{t('months:bankEvidence.bankFeeTitle')}</strong>
                    <div className="reason">{t('months:bankEvidence.bankFeeDate')}</div>
                    <span className="badge badge-outline">
                      <Icon name="building" size="sm" />
                      {t('months:bankEvidence.bankRecorded')}
                    </span>
                  </td>
                  <td className="r num">{t('months:bankEvidence.bankFeeAmount')}</td>
                  <td data-cell="wide">
                    <span className="match-chip none">
                      <Icon name="file-text" size="sm" />
                      <span>{t('months:bankEvidence.noSupportingDoc')}</span>
                    </span>
                    <p className="reason">{t('months:bankEvidence.noInvoiceAttached')}</p>
                    <p className="reason">{t('months:bankEvidence.missingSupportNote')}</p>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <details className="disclosure">
            <summary>
              {t('months:bankEvidence.explainSummary')} <Icon name="chevron-down" size="sm" />
            </summary>
            <div className="stack gap-3 mt-3">
              <p>{t('months:bankEvidence.feeCounts', { currency })}</p>
              <label className="field">
                {t('months:bankEvidence.reason')}
                <textarea
                  className="input"
                  rows={2}
                  defaultValue={t('months:bankEvidence.feeDefaultReason')}
                />
              </label>
              <Button
                variant="secondary"
                size="lg"
                onClick={() => setFeedback(t('months:bankEvidence.supportRecordedFeedback'))}
              >
                {t('months:bankEvidence.noDocNeeded')}
              </Button>
            </div>
          </details>

          <p className="muted">{t('months:bankEvidence.footerNote')}</p>
          <div>
            <Link to="/months/2026-03" className="button button-secondary button-lg">
              {t('months:bankEvidence.seeMarch')}
            </Link>
          </div>
        </section>
      )}

      {tab === 'documents' && (
        <section className="stack gap-4" aria-labelledby="documents-first-h">
          <h2 className="type-h2" id="documents-first-h">
            {t('months:documentsFirst.title')}
          </h2>
          <p>{t('months:documentsFirst.description')}</p>
          <div className="table-panel rt-wrap">
            <table className="data-table rt">
              <thead>
                <tr>
                  <th>{t('months:documentsFirst.colDocument')}</th>
                  <th className="r">{t('months:documentsFirst.colAmount', { currency })}</th>
                  <th>{t('months:documentsFirst.colPaymentEvidence')}</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>
                    <strong>{t('months:documentsFirst.primepack')}</strong>
                    <div className="reason">{t('months:documentsFirst.primepackSub')}</div>
                  </td>
                  <td className="r num">{t('months:documentsFirst.primepackAmount')}</td>
                  <td data-cell="wide">
                    <span className="match-chip none">
                      <Icon name="clock" size="sm" />
                      <span>{t('months:documentsFirst.waitingStatement')}</span>
                    </span>
                    <p className="reason">{t('months:documentsFirst.notConfirmedNoCash')}</p>
                  </td>
                </tr>
                <tr>
                  <td>
                    <strong>{t('months:documentsFirst.greenValley')}</strong>
                    <div className="reason">{t('months:documentsFirst.greenValleySub')}</div>
                  </td>
                  <td className="r num">{t('months:documentsFirst.greenValleyAmount')}</td>
                  <td data-cell="wide">
                    <span className="match-chip manual">
                      <Icon name="hand" size="sm" />
                      <span>{t('months:documentsFirst.paymentConfirmedByYou')}</span>
                    </span>
                    <p className="reason">
                      {t('months:documentsFirst.confirmedCashNote', { currency })}
                    </p>
                  </td>
                </tr>
                <tr>
                  <td>
                    <strong>{t('months:documentsFirst.cendana')}</strong>
                    <div className="reason">{t('months:documentsFirst.cendanaSub')}</div>
                  </td>
                  <td className="r num">{t('months:documentsFirst.cendanaAmount')}</td>
                  <td data-cell="wide">
                    <span className="match-chip manual">
                      <Icon name="hand" size="sm" />
                      <span>{t('months:documentsFirst.docApproved')}</span>
                    </span>
                    <p className="reason">{t('months:documentsFirst.waitingApprovalNote')}</p>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <div className="stack gap-3">
            <h3 className="type-h3">{t('months:documentsFirst.chooseConfirmTitle')}</h3>
            <p>{t('months:documentsFirst.chooseConfirmDesc')}</p>
            <div className="row">
              <Button
                variant="secondary"
                size="lg"
                onClick={() => setFeedback(t('months:documentsFirst.approvalFeedback'))}
              >
                {t('months:documentsFirst.approveDoc')}
              </Button>
              <Link to="/documents?upload=1" className="button button-secondary button-lg">
                {t('months:documentsFirst.uploadStatement')}
              </Link>
            </div>

            <details className="disclosure" open>
              <summary>
                {t('months:documentsFirst.manualPaymentSummary')} <Icon name="chevron-down" size="sm" />
              </summary>
              <form
                className="stack gap-3 mt-3"
                onSubmit={(e) => {
                  e.preventDefault()
                  setFeedback(t('months:documentsFirst.manualPaymentFeedback'))
                }}
              >
                <label className="field">
                  {t('months:documentsFirst.amountPaid', { currency })}
                  <input
                    className="input"
                    type="number"
                    defaultValue="450.00"
                    min="0.01"
                    max="450"
                    step="0.01"
                    required
                  />
                </label>
                <label className="field">
                  {t('months:documentsFirst.paymentDate')}
                  <input className="input" type="date" defaultValue="2026-07-15" required />
                </label>
                <label className="field">
                  {t('months:documentsFirst.paymentMethod')}
                  <select className="select">
                    <option>{t('months:documentsFirst.methodTransfer')}</option>
                    <option>{t('months:documentsFirst.methodCash')}</option>
                    <option>{t('months:documentsFirst.methodCard')}</option>
                  </select>
                </label>
                <label className="field">
                  {t('months:documentsFirst.reason')}
                  <textarea
                    className="input"
                    rows={2}
                    defaultValue={t('months:documentsFirst.paymentReasonDefault')}
                    required
                  />
                </label>
                <p className="muted">{t('months:documentsFirst.auditNotice')}</p>
                <Button type="submit" size="lg">
                  {t('months:documentsFirst.confirmManualPayment')}
                </Button>
              </form>
            </details>
          </div>
        </section>
      )}

      {tab === 'currency' && (
        <section className="stack gap-4" aria-labelledby="currency-check-h">
          <h2 className="type-h2" id="currency-check-h">
            {t('months:currencyCheck.title')}
          </h2>
          <p>{t('months:currencyCheck.workspaceUses', { currency })}</p>
          <span className="badge badge-medium">
            <Icon name="shield-alert" size="sm" />
            {t('months:currencyCheck.badgeNeedsConfirmation')}
          </span>
          <p>{t('months:currencyCheck.questionPrompt', { currency })}</p>
          <p className="muted">{t('months:currencyCheck.auditNotice')}</p>
          <div className="row">
            <Button
              size="lg"
              onClick={() => setFeedback(t('months:currencyCheck.currencyFeedback', { currency }))}
            >
              {t('months:currencyCheck.useAmountsAs', { currency })}
            </Button>
            <Link to="/documents" className="button button-secondary button-lg">
              {t('months:currencyCheck.replaceDoc')}
            </Link>
          </div>
        </section>
      )}
    </div>
  )
}
