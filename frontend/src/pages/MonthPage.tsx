/**
 * MonthPage: one month's reconciliation workbench (spec 007, AC-007-12…19; mock month.html).
 *
 * Every figure is a fact of the month run (docs/08 §5): when a fact does not exist the page says
 * so instead of showing a number. Support and categories are labelled by their own state, so a
 * line matched by Kredibel, one waiting for a document and one between own accounts look different.
 */

import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { type BankLine, CASHFLOW_BADGE, isIncoming, useMonthBankLines } from '../entities/bank-line'
import { useFindings } from '../entities/finding'
import { type Match, useMatches, useUnmatch } from '../entities/match'
import { useMonth, useMonths, useReconcileMonth } from '../entities/month'
import { useWorkspace } from '../entities/workspace'
import { formatDate, formatMonth } from '../shared/lib/formatDate'
import { formatAmount } from '../shared/lib/formatMoney'
import { Badge, Button, DataTable, type DataTableColumn, type DataTableFilter, Icon } from '../shared/ui'
import type { IconName } from '../shared/ui/Icon'
import { MatchSheet, MonthDocuments, MonthFindings, useMonthDocuments } from '../widgets/month'

type Tab = 'lines' | 'documents' | 'ledger' | 'findings'
const TABS: Tab[] = ['lines', 'documents', 'ledger', 'findings']

type Support = 'AUTO' | 'MANUAL' | 'PROPOSED' | 'NOT_REQUIRED' | 'EXCLUDED' | 'NO_SUPPORT' | 'NOT_RUN'
type Figures = Record<string, { value?: string } | undefined> | undefined

const SUPPORT_CHIP: Record<Support, { chip: string; icon: IconName }> = {
  AUTO: { chip: 'auto', icon: 'link' },
  MANUAL: { chip: 'manual', icon: 'hand' },
  PROPOSED: { chip: 'proposed', icon: 'eye' },
  NOT_REQUIRED: { chip: 'cleared', icon: 'check' },
  EXCLUDED: { chip: 'excluded', icon: 'refresh' },
  NO_SUPPORT: { chip: 'none', icon: 'file-text' },
  NOT_RUN: { chip: 'none', icon: 'clock' },
}
const STATE_BADGE = {
  COLLECTING: 'outline',
  RECONCILING: 'low',
  NEEDS_REVIEW: 'medium',
  RECONCILED: 'clean',
  SIGNED_OFF: 'clean',
} as const
const MARK = {
  AGREED: 'reading-agreed',
  SINGLE_SOURCE: 'reading-single',
  CONFLICT: 'reading-conflict',
  MISSING: 'reading-conflict',
} as const

/** What supports a bank line (ADR-025), from the month run's state and the match's method. */
function supportOf(line: BankLine, match: Match | undefined): Support {
  switch (line.support) {
    case 'MATCHED':
      return match?.method === 'MANUAL' || line.match?.state === 'MANUAL' ? 'MANUAL' : 'AUTO'
    case 'PROPOSED':
    case 'NOT_REQUIRED':
    case 'EXCLUDED':
    case 'NO_SUPPORT':
      return line.support
    default:
      return 'NOT_RUN'
  }
}

function value(figures: Figures, name: string): string | undefined {
  return figures?.[name]?.value ?? undefined
}

function count(figures: Figures, name: string): number {
  return Number(value(figures, name) ?? 0)
}

function monthAround(month: string) {
  const [year, number] = month.split('-').map((part) => parseInt(part, 10))
  const shift = (by: number) => {
    const d = new Date(Date.UTC(year || 2026, (number || 1) - 1 + by, 1))
    return `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, '0')}`
  }
  const label = new Date(Date.UTC(year || 2026, (number || 1) - 1, 1)).toLocaleDateString('en-US', {
    month: 'long',
    year: 'numeric',
    timeZone: 'UTC',
  })
  return { previous: shift(-1), next: shift(1), label }
}

export function MonthPage() {
  const { t } = useTranslation(['months', 'common'])
  const { month = '' } = useParams<{ month: string }>()
  const { data: monthData, isLoading: monthLoading } = useMonth(month)
  const { data: monthsList } = useMonths()
  const [params, setParams] = useSearchParams()
  const asked = params.get('tab') as Tab | null
  const tab: Tab = asked && TABS.includes(asked) ? asked : 'lines'
  const { rows: monthDocuments } = useMonthDocuments(month)
  const { data: findingsData } = useFindings({ month })
  const openFindings = (findingsData?.items ?? []).filter((f) => f.status === 'OPEN' || f.status === 'ACKNOWLEDGED')
  const { data: linesData, isLoading: linesLoading } = useMonthBankLines(month)
  const { data: matchesData } = useMatches(month)
  const { data: ws } = useWorkspace(true)
  const reconcileMutation = useReconcileMonth()
  const unmatchMutation = useUnmatch()

  const [matchingLine, setMatchingLine] = useState<BankLine | null>(null)
  const [statusMessage, setStatusMessage] = useState<string | null>(null)

  const lines = linesData?.items ?? []
  // A month with nothing in it (often this calendar month) says so and points to the latest month
  // that has data, instead of a page of dashes.
  const latestWithData = (monthsList?.items ?? [])
    .filter((m) => m.month !== month && Object.keys(m.figures ?? {}).length > 0)
    .map((m) => m.month)
    .sort()
    .at(-1)
  const isEmpty =
    !monthLoading &&
    !linesLoading &&
    lines.length === 0 &&
    monthDocuments.length === 0 &&
    Object.keys(monthData?.figures ?? {}).length === 0
  const matches = matchesData?.items ?? []
  const currency = ws?.currency ?? lines[0]?.amount?.currency ?? ''
  const figures = monthData?.figures as Figures
  const risk = monthData?.risk
  const { previous, next, label: monthLabel } = monthAround(month)
  const matchOf = (line: BankLine) => matches.find((m) => m.matchId === line.match?.matchIds?.[0])
  const support = (line: BankLine) => supportOf(line, matchOf(line))

  const amount = (name: string, absolute = false) => {
    const v = value(figures, name)
    if (v === undefined) return undefined
    return formatAmount(absolute ? v.replace(/^-/, '') : v, { currency })
  }
  const opening = amount('opening')
  const closing = amount('closing')
  const moneyIn = amount('moneyIn')
  const moneyOut = amount('moneyOut', true)
  const ledgerDifference = amount('ledgerDifference')
  const autoRate = value(figures, 'autoMatchRate')
  const autoPercent = autoRate === undefined ? undefined : Math.round(Number(autoRate) * 100)
  const inScope = count(figures, 'bankLines') - count(figures, 'excluded')
  const meter = {
    auto: count(figures, 'autoMatched'),
    manual: count(figures, 'manuallyMatched'),
    open: count(figures, 'proposed') + count(figures, 'unmatched'),
  }
  const meterTotal = meter.auto + meter.manual + meter.open
  const share = (n: number) => `${((n / meterTotal) * 100).toFixed(1)}%`
  const credits = lines.filter(isIncoming).length


  const handleUnmatch = async (matchId: string) => {
    try {
      await unmatchMutation.mutateAsync(matchId)
      setStatusMessage(t('months:monthDetail.unmatchedStatus'))
    } catch {
      setStatusMessage(t('months:monthDetail.unmatchFailed'))
    }
  }

  const isOpen = (line: BankLine) => ['PROPOSED', 'NO_SUPPORT', 'NOT_RUN'].includes(support(line))
  const filters: DataTableFilter<BankLine>[] = [
    { key: 'all', label: t('months:monthDetail.filterAll'), predicate: () => true, count: lines.length },
    { key: 'open', label: t('months:monthDetail.filterOpen'), predicate: isOpen, count: lines.filter(isOpen).length },
    { key: 'in', label: t('months:monthDetail.filterIn'), predicate: isIncoming, count: credits },
    {
      key: 'out',
      label: t('months:monthDetail.filterOut'),
      predicate: (line) => !isIncoming(line),
      count: lines.length - credits,
    },
  ]

  const categoryLabel = (line: BankLine) => t(`months:categories.${line.category ?? 'UNKNOWN'}`)

  const columns: DataTableColumn<BankLine>[] = [
    {
      key: 'bankLine',
      header: t('months:monthDetail.colBankLine'),
      wideOnMobile: true,
      sortable: true,
      sortValue: (line) => line.date,
      render: (line) => {
        const cashflow = line.cashflowClass ?? 'UNCLASSIFIED'
        const [first] = line.description.split('\n')
        return (
          <div className="stack gap-1">
            <strong>{line.counterpartyName || first}</strong>
            <div className="reason">{formatDate(line.date)}</div>
            <div className="row gap-2 items-center flex-wrap">
              <Badge
                variant={CASHFLOW_BADGE[cashflow]}
                aria-label={t('months:monthDetail.categoryAria', {
                  category: categoryLabel(line),
                  cashflow: t(`months:cashflow.${cashflow}`),
                })}
              >
                {categoryLabel(line)}
              </Badge>
              {cashflow && cashflow !== 'UNCLASSIFIED' && (
                <Badge variant="outline">
                  {t('months:ifrsLabel', { classification: t(`months:cashflow.${cashflow}`) })}
                </Badge>
              )}
              {line.categorizedBy === 'USER' && (
                <span className="reason">{t('months:monthDetail.categoryByYou')}</span>
              )}
            </div>
          </div>
        )
      },
    },
    {
      key: 'amount',
      header: t('months:monthDetail.colAmount', { currency }),
      align: 'right',
      sortable: true,
      sortValue: (line) => Number(line.amount?.amount ?? 0),
      render: (line) => {
        const incoming = isIncoming(line)
        const status = line.readings?.amount?.status ?? 'AGREED'
        return (
          <span className={incoming ? 'amt-in' : 'amt-out'}>
            <span className={`reading ${MARK[status]}`}>
              {incoming ? '+' : ''}
              {formatAmount(line.amount?.amount ?? '0', { currency })}
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
        const kind = support(line)
        const reasons = matchOf(line)?.reasons ?? []
        const reason =
          (kind === 'AUTO' || kind === 'MANUAL') && reasons.length
            ? reasons.map((r) => t(`months:monthDetail.matchReasons.${r}`, { defaultValue: r })).join(', ')
            : kind === 'AUTO' || kind === 'MANUAL'
              ? ''
              : t(`months:monthDetail.supportReason.${kind}`)
        return (
          <div>
            <span className={`match-chip ${SUPPORT_CHIP[kind].chip}`}>
              <Icon name={SUPPORT_CHIP[kind].icon} size="sm" />
              <span>{t(`months:monthDetail.support.${kind}`)}</span>
            </span>
            {reason && <div className="reason">{reason}</div>}
          </div>
        )
      },
    },
    {
      key: 'actions',
      header: t('months:monthDetail.colActions'),
      align: 'right',
      render: (line) => {
        const kind = support(line)
        const matchId = line.match?.matchIds?.[0]
        if (kind === 'EXCLUDED' || kind === 'NOT_RUN') return null
        if ((kind === 'AUTO' || kind === 'MANUAL') && matchId) {
          return (
            <Button variant="secondary" size="sm" onClick={() => void handleUnmatch(matchId)}>
              {t('months:monthDetail.unmatch')}
            </Button>
          )
        }
        return (
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setMatchingLine(line)}
          >
            {t('months:monthDetail.match')}
          </Button>
        )
      },
    },
  ]

  const noValue = t('months:monthDetail.noValue')
  const figure = (shown: string | undefined) =>
    shown === undefined ? (
      noValue
    ) : (
      <>
        <small>{currency}</small>
        {shown}
      </>
    )

  return (
    <div className="page">
      <div className="month-head">
        <div className="row">
          <span className="month-switch">
            <Link to={`/months/${previous}`} aria-label={t('months:monthDetail.previousMonth')}>
              <Icon name="chevron-left" />
            </Link>
            <Link to={`/months/${next}`} aria-label={t('months:monthDetail.nextMonth')}>
              <Icon name="chevron-right" />
            </Link>
          </span>
          <h1 className="type-title">{monthLabel}</h1>
          <Link className="link small" to="/months/all">
            {t('months:monthDetail.allMonths')}
          </Link>
          {monthData?.state && (
            <Badge variant={STATE_BADGE[monthData.state]}>{t(`months:monthDetail.states.${monthData.state}`)}</Badge>
          )}
          {risk?.level === 'CRITICAL' && (
            <Badge variant="critical">
              <Icon name="shield-alert" size="sm" />
              {t('months:monthDetail.critical')}
            </Badge>
          )}
          <Link
            className="button button-quiet button-sm ml-auto"
            to={`/assistant?q=${encodeURIComponent(`What is the reconciliation status and risk for ${monthLabel}?`)}`}
          >
            <Icon name="sparkles" size="sm" />
            {t('months:monthDetail.askAboutMonth')}
          </Link>
        </div>

        <p className="muted">{monthData?.note || t('months:monthDetail.subtitle')}</p>
      </div>

      {statusMessage && (
        <p className="muted mt-3" role="status">
          {statusMessage}
        </p>
      )}

      {isEmpty ? (
        <section className="panel panel-pad stack gap-3 mt-6" aria-labelledby="month-empty-h">
          <h2 className="type-h3" id="month-empty-h">
            {t('months:monthDetail.empty.title', { month: monthLabel })}
          </h2>
          <p className="muted">
            {latestWithData
              ? t('months:monthDetail.empty.hasOthers', { month: formatMonth(latestWithData) })
              : t('months:monthDetail.empty.nothingYet')}
          </p>
          <div className="row gap-2 flex-wrap">
            {latestWithData && (
              <Link className="button button-primary button-sm" to={`/months/${latestWithData}`}>
                {t('months:monthDetail.empty.openLatest', { month: formatMonth(latestWithData) })}
              </Link>
            )}
            <Link className="button button-secondary button-sm" to="/documents?upload=1">
              {t('months:monthDetail.empty.upload')}
            </Link>
          </div>
        </section>
      ) : (
        <div className="stack gap-6 mt-6">
          <section className="ledger" aria-label={t('months:monthDetail.figuresAria', { month: monthLabel })}>
            <dl className="ledger-figures">
              <div>
                <dt>{t('months:monthDetail.openingBalance')}</dt>
                <dd className="v">{figure(opening)}</dd>
                <dd className="n">
                  {opening === undefined ? t('months:monthDetail.noBalances') : t('months:monthDetail.fromPreviousClosing')}
                </dd>
              </div>
              <div>
                <dt>{t('months:monthDetail.moneyIn')}</dt>
                <dd className="v">{figure(moneyIn)}</dd>
                <dd className="n">{t('months:monthDetail.creditsRecorded', { count: credits })}</dd>
              </div>
              <div>
                <dt>{t('months:monthDetail.moneyOut')}</dt>
                <dd className="v">{figure(moneyOut)}</dd>
                <dd className="n">{t('months:monthDetail.debitsRecorded', { count: lines.length - credits })}</dd>
              </div>
              <div>
                <dt>{t('months:monthDetail.closingBalance')}</dt>
                <dd className="v">{figure(closing)}</dd>
                <dd className="n">
                  {closing === undefined ? t('months:monthDetail.noBalances') : t('months:monthDetail.asPrintedOnStatement')}
                </dd>
              </div>
              <div>
                <dt>{t('months:monthDetail.matchedByKredibel')}</dt>
                <dd className="v">{autoPercent === undefined ? noValue : `${autoPercent}%`}</dd>
                <dd className="n">
                  {t('months:monthDetail.allocatedToDocs', { matched: count(figures, 'autoMatched'), total: Math.max(inScope, 0) })}
                </dd>
                {autoPercent !== undefined && (
                  <dd className="mini">
                    <i style={{ width: `${autoPercent}%` }} /* allow-raw-style: the month's automatic match rate */ />
                  </dd>
                )}
              </div>
              <div>
                <dt>{t('months:monthDetail.ledgerDifference')}</dt>
                <dd className="v">{figure(ledgerDifference)}</dd>
                <dd className="n">
                  {ledgerDifference === undefined ? t('months:monthDetail.noLedger') : t('months:monthDetail.differenceWithLedger')}
                </dd>
              </div>
            </dl>
          </section>

          {risk?.summary && (
            <section className="explain" aria-labelledby="ex-h">
              <h2 className="explain-head" id="ex-h">
                <Icon name="shield-alert" />
                {t(`months:monthDetail.explainHead.${risk.level}`)}
              </h2>
              <div className="explain-body">
                <p className="lead">{risk.summary.replace(/\s*\[\[[^\]]*\]\]/g, '')}</p>
                {(risk.nextSteps?.length ?? 0) > 0 && (
                  <div className="stack gap-2">
                    <h3 className="type-h3">{t('months:monthDetail.whatNext')}</h3>
                    <ol className="steps">
                      {risk.nextSteps?.map((step) => <li key={step}>{step}</li>)}
                    </ol>
                  </div>
                )}
                <span className="by-line">
                  <Icon name="sparkles" size="sm" />
                  {t('months:monthDetail.byline')}
                </span>
              </div>
            </section>
          )}

          {meterTotal > 0 && (
            <section className="recon-meter" aria-label={t('months:monthDetail.meterAria')}>
              <div className="bar">
                <i className="auto" style={{ width: share(meter.auto) }} /* allow-raw-style: share of the month's lines */ />
                <i className="manual" style={{ width: share(meter.manual) }} /* allow-raw-style: share of the month's lines */ />
                <i className="open" style={{ width: share(meter.open) }} /* allow-raw-style: share of the month's lines */ />
              </div>
              <p className="key">
                <span>
                  <i className="auto"></i>
                  {t('months:monthDetail.matchedByKredibel')} <b>{meter.auto}</b>
                </span>
                <span>
                  <i className="manual"></i>
                  {t('months:monthDetail.matchedByYou')} <b>{meter.manual}</b>
                </span>
                <span>
                  <i className="open"></i>
                  {t('months:monthDetail.open')} <b>{meter.open}</b>
                </span>
              </p>
            </section>
          )}

          <nav className="tabs" role="tablist" aria-label={t('months:monthDetail.sectionsAria', { month: monthLabel })}>
            {TABS.map((key) => {
              const count =
                key === 'lines' ? lines.length : key === 'documents' ? monthDocuments.length : key === 'findings' ? openFindings.length : undefined
              return (
                <button
                  key={key}
                  type="button"
                  role="tab"
                  id={`month-tab-${key}`}
                  aria-controls="month-tabpanel"
                  aria-selected={tab === key}
                  className="tab"
                  onClick={() => setParams(key === 'lines' ? {} : { tab: key }, { replace: true })}
                >
                  {t(`months:monthDetail.tabs.${key}`)}
                  {count !== undefined && (
                    <span className={`count${key === 'findings' && count > 0 ? ' is-attn' : ''}`}>{count}</span>
                  )}
                </button>
              )
            })}
          </nav>

          <div role="tabpanel" id="month-tabpanel" aria-labelledby={`month-tab-${tab}`}>
            {tab === 'lines' && (
            <DataTable
              data={lines}
              columns={columns}
              getRowKey={(line) => line.txId}
              filters={filters}
              filterGroupAriaLabel={t('months:monthDetail.filterBankLines')}
              searchable={true}
              searchPlaceholder={t('months:monthDetail.searchPlaceholder')}
              searchPredicate={(line, q) =>
                [line.description, line.counterpartyName, categoryLabel(line), line.date, line.amount?.amount]
                  .filter(Boolean)
                  .some((text) => String(text).toLowerCase().includes(q))
              }
              isLoading={linesLoading}
              loadingMessage={<p>{t('months:monthDetail.loadingBankLines')}</p>}
              emptyMessage={<p className="muted">{t('months:monthDetail.noBankLinesFilter')}</p>}
              headerActions={
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={reconcileMutation.isPending}
                  onClick={() => reconcileMutation.mutate(month)}
                >
                  {reconcileMutation.isPending ? t('months:monthDetail.reconciling') : t('months:monthDetail.reReconcile')}
                </Button>
              }
              footer={
                <p className="reading-legend">
                  <span>
                    <span className="reading reading-agreed">{t('months:monthDetail.legendSample')}</span>{' '}
                    {t('months:monthDetail.legendAgreed')}
                  </span>
                  <span>
                    <span className="reading reading-single">{t('months:monthDetail.legendSample')}</span>{' '}
                    {t('months:monthDetail.legendSingle')}
                  </span>
                  <span>
                    <span className="reading reading-conflict">{t('months:monthDetail.legendSample')}</span>{' '}
                    {t('months:monthDetail.legendConflict')}
                  </span>
                </p>
              }
            />
            )}
            {tab === 'documents' && <MonthDocuments month={month} currency={currency} />}
            {tab === 'ledger' && (
              <div className="stack gap-3">
                <p className="muted">{t('months:monthDetail.ledger.none')}</p>
                <Link className="button button-secondary button-sm self-start" to="/documents?upload=1">
                  {t('months:monthDetail.ledger.upload')}
                </Link>
              </div>
            )}
            {tab === 'findings' && <MonthFindings findings={openFindings} />}
          </div>
        </div>
      )}
      {matchingLine && (
        <MatchSheet
          line={matchingLine}
          month={month}
          currency={currency}
          documents={monthDocuments}
          onClose={() => setMatchingLine(null)}
          onMatched={(id) => {
            setStatusMessage(t('months:monthDetail.matchedStatus', { id }))
            setMatchingLine(null)
          }}
          onNotRequired={() => {
            setStatusMessage(
              t('months:monthDetail.matchSheet.noDocSuccess', {
                defaultValue: 'Marked as needing no document. Reconciling month...',
              }),
            )
            setMatchingLine(null)
          }}
        />
      )}
    </div>
  )
}
