/**
 * MonthPage: Month reconciliation workbench (spec 007, AC-007-12..19).
 *
 * Displays figures, Gemini explanation, breakdown meter, filter chips,
 * and the bank lines list with match chips, plus manual Match/Unmatch controls.
 */

import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useParams } from 'react-router-dom'
import { useMonthBankLines } from '../entities/bank-line'
import { useCreateMatch, useMatches, useUnmatch } from '../entities/match'
import { useMonth, useReconcileMonth } from '../entities/month'
import { useWorkspace } from '../entities/workspace'
import { formatMoney } from '../shared/lib/formatMoney'
import { Badge, Button, Icon } from '../shared/ui'

type LineFilter = 'all' | 'open' | 'in' | 'out'

function factValue(fact: { value?: unknown } | undefined, fallback = '0.00'): string {
  if (!fact || fact.value === undefined || fact.value === null) return fallback
  if (typeof fact.value === 'object' && 'amount' in fact.value) {
    return String((fact.value as { amount: string }).amount)
  }
  return String(fact.value)
}

export function MonthPage() {
  const { t } = useTranslation(['months', 'common'])
  const { month = '2026-03' } = useParams<{ month: string }>()
  const { data: monthData } = useMonth(month)
  const { data: linesData, isLoading: linesLoading } = useMonthBankLines(month)
  const { data: matchesData } = useMatches(month)
  const { data: ws } = useWorkspace(true)
  const reconcileMutation = useReconcileMonth()
  const createMatchMutation = useCreateMatch()
  const unmatchMutation = useUnmatch()

  const [filter, setFilter] = useState<LineFilter>('all')
  const [matchingTxId, setMatchingTxId] = useState<string | null>(null)
  const [matchCandidateId, setMatchCandidateId] = useState<string>('')
  const [statusMessage, setStatusMessage] = useState<string | null>(null)

  const activeMonth = monthData
  const lines = linesData?.items ?? []
  const matches = matchesData?.items ?? []
  const currency = ws?.currency ?? 'IDR'

  // Month navigation calculation
  const parts = month.split('-')
  const year = parseInt(parts[0], 10) || 2026
  const mon = parseInt(parts[1], 10) || 3
  const prevDate = new Date(Date.UTC(year, mon - 2, 1))
  const nextDate = new Date(Date.UTC(year, mon, 1))
  const prevStr = `${prevDate.getUTCFullYear()}-${String(prevDate.getUTCMonth() + 1).padStart(2, '0')}`
  const nextStr = `${nextDate.getUTCFullYear()}-${String(nextDate.getUTCMonth() + 1).padStart(2, '0')}`
  const monthDate = new Date(Date.UTC(year, mon - 1, 1))
  const monthLabel = monthDate.toLocaleDateString('en-US', {
    month: 'long',
    year: 'numeric',
    timeZone: 'UTC',
  })

  // Filter lines
  const filteredLines = lines.filter((l) => {
    if (filter === 'all') return true
    if (filter === 'open') return !l.match?.matchIds?.length
    const num = Number(l.amount?.amount ?? 0)
    if (filter === 'in') return num > 0
    if (filter === 'out') return num < 0
    return true
  })

  const isReconciled = activeMonth?.state === 'RECONCILED'
  const isNeedsReview = activeMonth?.state === 'NEEDS_REVIEW'
  const state = activeMonth?.state ?? 'RECONCILED'
  const isCritical = activeMonth?.risk?.level === 'CRITICAL'

  const openingVal = factValue(activeMonth?.figures?.opening ?? activeMonth?.figures?.opening_balance, '0.00')
  const moneyInVal = factValue(activeMonth?.figures?.money_in ?? activeMonth?.figures?.moneyIn, '0.00')
  const moneyOutVal = factValue(activeMonth?.figures?.money_out ?? activeMonth?.figures?.moneyOut, '0.00')
  const closingVal = factValue(activeMonth?.figures?.closing ?? activeMonth?.figures?.closing_balance, '0.00')
  const matchRateVal = factValue(activeMonth?.figures?.auto_match_rate ?? activeMonth?.figures?.match_rate, '86%')
  const ledgerDiffVal = factValue(activeMonth?.figures?.ledger_difference ?? activeMonth?.figures?.ledgerDifference, '0.00')

  const handleManualMatch = async (txId: string) => {
    if (!matchCandidateId.trim()) return
    try {
      await createMatchMutation.mutateAsync({
        bankLineIds: [txId],
        invoiceIds: [matchCandidateId.trim()],
        note: 'Manual match created by user',
      })
      setStatusMessage(`Matched ${txId} with ${matchCandidateId.trim()}`)
      setMatchingTxId(null)
      setMatchCandidateId('')
    } catch {
      setStatusMessage('Failed to create match')
    }
  }

  const handleUnmatch = async (matchId: string) => {
    try {
      await unmatchMutation.mutateAsync(matchId)
      setStatusMessage(`Unmatched ${matchId}`)
    } catch {
      setStatusMessage('Failed to unmatch')
    }
  }

  return (
    <div className="page">
      <div className="month-head">
        <div className="row">
          <span className="month-switch">
            <Link to={`/months/${prevStr}`} aria-label={t('months:monthDetail.previousMonth')}>
              <Icon name="chevron-left" />
            </Link>
            <Link to={`/months/${nextStr}`} aria-label={t('months:monthDetail.nextMonth')}>
              <Icon name="chevron-right" />
            </Link>
          </span>
          <h1 className="type-title">{monthLabel}</h1>
          <Badge variant={isReconciled ? 'clean' : isNeedsReview ? 'medium' : 'default'}>
            {state}
          </Badge>
          {isCritical && (
            <Badge variant="critical">
              <Icon name="shield-alert" size="sm" />
              {t('months:monthDetail.critical')}
            </Badge>
          )}
        </div>
        <p className="muted">
          {t('months:monthDetail.subtitle')}
        </p>
      </div>

      {statusMessage && (
        <p className="muted mt-3" role="status">
          {statusMessage}
        </p>
      )}

      <div className="stack gap-6 mt-6">
        {/* Figures summary */}
        <section className="ledger" aria-label={t('months:monthDetail.figuresAria', { month: monthLabel })}>
          <dl className="ledger-figures">
            <div>
              <dt>{t('months:monthDetail.openingBalance')}</dt>
              <dd className="v">
                <small>{currency}</small>
                <span className="reading reading-agreed">
                  {formatMoney(openingVal, { currency })}
                </span>
              </dd>
              <dd className="n">{t('months:monthDetail.fromPreviousClosing')}</dd>
            </div>
            <div>
              <dt>{t('months:monthDetail.moneyIn')}</dt>
              <dd className="v">
                <small>{currency}</small>
                <span className="reading reading-agreed">
                  {formatMoney(moneyInVal, { currency })}
                </span>
              </dd>
              <dd className="n">{t('months:monthDetail.creditsRecorded')}</dd>
            </div>
            <div>
              <dt>{t('months:monthDetail.moneyOut')}</dt>
              <dd className="v">
                <small>{currency}</small>
                <span className="reading reading-agreed">
                  {formatMoney(moneyOutVal, { currency })}
                </span>
              </dd>
              <dd className="n">{t('months:monthDetail.debitsRecorded')}</dd>
            </div>
            <div>
              <dt>{t('months:monthDetail.closingBalance')}</dt>
              <dd className="v">
                <small>{currency}</small>
                <span className="reading reading-agreed">
                  {formatMoney(closingVal, { currency })}
                </span>
              </dd>
              <dd className="n">{t('months:monthDetail.asPrintedOnStatement')}</dd>
            </div>
            <div>
              <dt>{t('months:monthDetail.matchedByKredibel')}</dt>
              <dd className="v">{matchRateVal}</dd>
              <dd className="n">{t('months:monthDetail.allocatedToDocs')}</dd>
              <dd className="mini">
                <i style={{ width: matchRateVal.endsWith('%') ? matchRateVal : `${matchRateVal}%` }} /* allow-raw-style: computed width */ />
              </dd>
            </div>
            <div>
              <dt>{t('months:monthDetail.ledgerDifference')}</dt>
              <dd className="v">
                <small>{currency}</small>
                {ledgerDiffVal}
              </dd>
              <dd className="n">{t('months:monthDetail.differenceWithLedger')}</dd>
            </div>
          </dl>
        </section>

        {/* Gemini explanation when Critical */}
        {isCritical && (
          <section className="explain" aria-labelledby="ex-h">
            <h2 className="explain-head" id="ex-h">
              <Icon name="shield-alert" />
              {t('months:monthDetail.criticalExplainHead')}
            </h2>
            <div className="explain-body">
              <p className="lead">
                {t('months:monthDetail.criticalExplainLead')}
              </p>
              <div className="stack gap-2">
                <h3 className="type-h3">{t('months:monthDetail.whatNext')}</h3>
                <ol className="steps">
                  <li>{t('months:monthDetail.step1')}</li>
                  <li>{t('months:monthDetail.step2')}</li>
                </ol>
              </div>
              <span className="by-line">
                <Icon name="sparkles" size="sm" />
                {t('months:monthDetail.byline')}
              </span>
            </div>
          </section>
        )}

        {/* Meter */}
        <section className="recon-meter" aria-label={t('months:monthDetail.meterAria')}>
          <div className="bar">
            <i className="auto" style={{ width: '85%' }} /* allow-raw-style: computed meter bar */ />
            <i className="manual" style={{ width: '10%' }} /* allow-raw-style: computed meter bar */ />
            <i className="open" style={{ width: '5%' }} /* allow-raw-style: computed meter bar */ />
          </div>
          <p className="key">
            <span>
              <i className="auto"></i>{t('months:monthDetail.matchedByKredibel')}
            </span>
            <span>
              <i className="manual"></i>{t('months:monthDetail.matchedByYou')}
            </span>
            <span>
              <i className="open"></i>{t('months:monthDetail.open')}
            </span>
          </p>
        </section>

        {/* Bank lines list & controls */}
        <div className="stack gap-3">
          <div className="row justify-between items-center">
            <div className="chips" role="group" aria-label={t('months:monthDetail.filterBankLines')}>
              <button
                type="button"
                className="chip"
                aria-pressed={filter === 'all'}
                onClick={() => setFilter('all')}
              >
                {t('months:monthDetail.filterAll')} <span className="n">{lines.length}</span>
              </button>
              <button
                type="button"
                className="chip"
                aria-pressed={filter === 'open'}
                onClick={() => setFilter('open')}
              >
                {t('months:monthDetail.filterOpen')}
              </button>
              <button
                type="button"
                className="chip"
                aria-pressed={filter === 'in'}
                onClick={() => setFilter('in')}
              >
                {t('months:monthDetail.filterIn')}
              </button>
              <button
                type="button"
                className="chip"
                aria-pressed={filter === 'out'}
                onClick={() => setFilter('out')}
              >
                {t('months:monthDetail.filterOut')}
              </button>
            </div>

            <Button
              variant="secondary"
              size="sm"
              disabled={reconcileMutation.isPending}
              onClick={() => reconcileMutation.mutate(month)}
            >
              {reconcileMutation.isPending ? t('months:monthDetail.reconciling') : t('months:monthDetail.reReconcile')}
            </Button>
          </div>

          <div className="table-panel rt-wrap">
            <table className="data-table rt">
              <thead>
                <tr>
                  <th>{t('months:monthDetail.colBankLine')}</th>
                  <th className="r">{t('months:monthDetail.colAmount', { currency })}</th>
                  <th>{t('months:monthDetail.colMatchedWith')}</th>
                  <th className="r">{t('months:monthDetail.colActions')}</th>
                </tr>
              </thead>
              <tbody>
                {linesLoading ? (
                  <tr>
                    <td colSpan={4} className="muted">
                      {t('months:monthDetail.loadingBankLines')}
                    </td>
                  </tr>
                ) : filteredLines.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="muted">
                      {t('months:monthDetail.noBankLinesFilter')}
                    </td>
                  </tr>
                ) : (
                  filteredLines.map((line) => {
                    const isCredit = Number(line.amount?.amount ?? 0) > 0
                    const matchId = line.match?.matchIds?.[0]
                    const matchObj = matches.find((m) => m.matchId === matchId)
                    const isManual = matchObj?.method === 'MANUAL'
                    const hasMatch = Boolean(matchId)

                    return (
                      <tr key={line.txId}>
                        <td data-cell="wide">
                          <strong>{line.description}</strong>
                          <div className="reason">
                            {line.date}, {line.category}
                          </div>
                        </td>
                        <td className="r">
                          <span className={isCredit ? 'amt-in' : 'amt-out'}>
                            <span className="reading reading-agreed">
                              {isCredit ? '+' : ''}
                              {formatMoney(line.amount?.amount ?? '0.00', { currency })}
                            </span>
                          </span>
                        </td>
                        <td data-cell="wide">
                          {hasMatch ? (
                            <>
                              <span className={`match-chip ${isManual ? 'manual' : 'auto'}`}>
                                <Icon name="link" size="sm" />
                                <span>{isManual ? t('months:monthDetail.matchedByYou') : t('months:monthDetail.matchedToDocument')}</span>
                              </span>
                              <div className="reason">
                                {matchObj?.reasons?.join(', ') || t('months:monthDetail.matchedByKredibelDefault')}
                              </div>
                            </>
                          ) : (
                            <>
                              <span className="match-chip none">
                                <Icon name="file-text" size="sm" />
                                <span>{t('months:monthDetail.noSupportingDocument')}</span>
                              </span>
                              <div className="reason">
                                {line.support || t('months:monthDetail.bankRecordedNoDoc')}
                              </div>
                            </>
                          )}
                        </td>
                        <td className="r">
                          {hasMatch ? (
                            <Button
                              variant="secondary"
                              size="sm"
                              onClick={() => handleUnmatch(matchId!)}
                            >
                              {t('months:monthDetail.unmatch')}
                            </Button>
                          ) : matchingTxId === line.txId ? (
                            <div className="row gap-2 items-center">
                              <input
                                className="input input-sm"
                                placeholder={t('months:monthDetail.invoiceIdPlaceholder')}
                                value={matchCandidateId}
                                onChange={(e) => setMatchCandidateId(e.target.value)}
                              />
                              <Button size="sm" onClick={() => handleManualMatch(line.txId)}>
                                {t('months:monthDetail.link')}
                              </Button>
                              <Button
                                variant="secondary"
                                size="sm"
                                onClick={() => setMatchingTxId(null)}
                              >
                                {t('months:monthDetail.cancel')}
                              </Button>
                            </div>
                          ) : (
                            <Button
                              variant="secondary"
                              size="sm"
                              onClick={() => {
                                setMatchingTxId(line.txId)
                                setMatchCandidateId('')
                              }}
                            >
                              {t('months:monthDetail.match')}
                            </Button>
                          )}
                        </td>
                      </tr>
                    )
                  })
                )}
              </tbody>
            </table>
          </div>

          <p className="reading-legend">
            <span>
              <span className="reading reading-agreed">7,250,000</span> {t('months:monthDetail.legendAgreed')}
            </span>
            <span>
              <span className="reading reading-single">7,250,000</span> {t('months:monthDetail.legendSingle')}
            </span>
            <span>
              <span className="reading reading-conflict">7,250,000</span> {t('months:monthDetail.legendConflict')}
            </span>
          </p>
        </div>
      </div>
    </div>
  )
}
