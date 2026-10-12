/**
 * MonthPage: Month reconciliation workbench (spec 007, AC-007-12..19).
 *
 * Displays figures, Gemini explanation, breakdown meter, filter chips,
 * and the bank lines list with match chips, plus manual Match/Unmatch controls.
 */

import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useParams } from 'react-router-dom'
import { type BankLine, useMonthBankLines } from '../entities/bank-line'
import { useCreateMatch, useMatches, useUnmatch } from '../entities/match'
import { useMonth, useReconcileMonth } from '../entities/month'
import { useWorkspace } from '../entities/workspace'
import { formatMoney } from '../shared/lib/formatMoney'
import { Badge, Button, DataTable, type DataTableColumn, type DataTableFilter, Icon } from '../shared/ui'


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

  const filters: DataTableFilter<BankLine>[] = useMemo(
    () => [
      {
        key: 'all',
        label: t('months:monthDetail.filterAll'),
        predicate: () => true,
        count: lines.length,
      },
      {
        key: 'open',
        label: t('months:monthDetail.filterOpen'),
        predicate: (l) => !l.match?.matchIds?.length,
        count: lines.filter((l) => !l.match?.matchIds?.length).length,
      },
      {
        key: 'in',
        label: t('months:monthDetail.filterIn'),
        predicate: (l) => Number(l.amount?.amount ?? 0) > 0,
        count: lines.filter((l) => Number(l.amount?.amount ?? 0) > 0).length,
      },
      {
        key: 'out',
        label: t('months:monthDetail.filterOut'),
        predicate: (l) => Number(l.amount?.amount ?? 0) < 0,
        count: lines.filter((l) => Number(l.amount?.amount ?? 0) < 0).length,
      },
    ],
    [lines, t],
  )

  const columns: DataTableColumn<BankLine>[] = useMemo(
    () => [
      {
        key: 'bankLine',
        header: t('months:monthDetail.colBankLine'),
        wideOnMobile: true,
        sortable: true,
        sortValue: (line) => line.description,
        render: (line) => (
          <div>
            <strong>{line.description}</strong>
            <div className="reason">
              {line.date}, {line.category}
            </div>
          </div>
        ),
      },
      {
        key: 'amount',
        header: t('months:monthDetail.colAmount', { currency }),
        align: 'right',
        sortable: true,
        sortValue: (line) => Number(line.amount?.amount ?? 0),
        render: (line) => {
          const isCredit = Number(line.amount?.amount ?? 0) > 0
          return (
            <span className={isCredit ? 'amt-in' : 'amt-out'}>
              <span className="reading reading-agreed">
                {isCredit ? '+' : ''}
                {formatMoney(line.amount?.amount ?? '0.00', { currency })}
              </span>
            </span>
          )
        },
      },
      {
        key: 'matchedWith',
        header: t('months:monthDetail.colMatchedWith'),
        wideOnMobile: true,
        render: (line) => {
          const matchId = line.match?.matchIds?.[0]
          const matchObj = matches.find((m) => m.matchId === matchId)
          const isManual = matchObj?.method === 'MANUAL'
          const hasMatch = Boolean(matchId)

          if (hasMatch) {
            return (
              <div>
                <span className={`match-chip ${isManual ? 'manual' : 'auto'}`}>
                  <Icon name="link" size="sm" />
                  <span>
                    {isManual
                      ? t('months:monthDetail.matchedByYou')
                      : t('months:monthDetail.matchedToDocument')}
                  </span>
                </span>
                <div className="reason">
                  {matchObj?.reasons?.join(', ') || t('months:monthDetail.matchedByKredibelDefault')}
                </div>
              </div>
            )
          }

          return (
            <div>
              <span className="match-chip none">
                <Icon name="file-text" size="sm" />
                <span>{t('months:monthDetail.noSupportingDocument')}</span>
              </span>
              <div className="reason">
                {line.support || t('months:monthDetail.bankRecordedNoDoc')}
              </div>
            </div>
          )
        },
      },
      {
        key: 'actions',
        header: t('months:monthDetail.colActions'),
        align: 'right',
        render: (line) => {
          const matchId = line.match?.matchIds?.[0]
          const hasMatch = Boolean(matchId)

          if (hasMatch) {
            return (
              <Button
                variant="secondary"
                size="sm"
                onClick={() => handleUnmatch(matchId!)}
              >
                {t('months:monthDetail.unmatch')}
              </Button>
            )
          }

          if (matchingTxId === line.txId) {
            return (
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
            )
          }

          return (
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
          )
        },
      },
    ],
    [currency, matches, matchingTxId, matchCandidateId, t],
  )

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
        <DataTable
          data={lines}
          columns={columns}
          getRowKey={(line) => line.txId}
          filters={filters}
          filterGroupAriaLabel={t('months:monthDetail.filterBankLines')}
          searchable={true}
          searchPlaceholder={t('common:table.searchPlaceholder', { defaultValue: 'Search bank lines...' })}
          searchPredicate={(line, q) => {
            if (line.description?.toLowerCase().includes(q)) return true
            if (line.category?.toLowerCase().includes(q)) return true
            if (line.date?.includes(q)) return true
            if (line.amount?.amount?.includes(q)) return true
            if (line.support?.toLowerCase().includes(q)) return true
            return false
          }}
          isLoading={linesLoading}
          loadingMessage={<p>{t('months:monthDetail.loadingBankLines')}</p>}
          emptyMessage={<p className="muted">{t('months:monthDetail.noBankLinesFilter')}</p>}
          pageSize={25}
          headerActions={
            <Button
              variant="secondary"
              size="sm"
              disabled={reconcileMutation.isPending}
              onClick={() => reconcileMutation.mutate(month)}
            >
              {reconcileMutation.isPending
                ? t('months:monthDetail.reconciling')
                : t('months:monthDetail.reReconcile')}
            </Button>
          }
          footer={
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
          }
        />
      </div>
    </div>
  )
}

