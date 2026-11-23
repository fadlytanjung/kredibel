/**
 * design/mocks/readiness.html (spec 025, AC-025-4, AC-025-5; ADR-028): whether the books are ready to
 * show a lender, the checks behind it with what to do next, the period's figures, the months with
 * their explained risk, the largest clients and what was read. Every figure and check comes from
 * GET /api/readiness (code); Print or save as PDF prints the page without the app's menus.
 */
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { useReadiness, type Readiness, type ReadinessCheck } from '../entities/readiness'
import { formatDate, formatMonth } from '../shared/lib/formatDate'
import { formatAmount } from '../shared/lib/formatMoney'
import { Button, EmptyState, Icon } from '../shared/ui'
import type { IconName } from '../shared/ui/icons.generated'
import { checkText, percent, periodText } from '../widgets/readiness'

type T = (key: string, options?: Record<string, unknown>) => string
type Money = { amount: string; currency: string } | null | undefined

const LEVEL: Record<Readiness['level'], { badge: string; icon: IconName }> = {
  READY: { badge: 'badge-clean', icon: 'shield-check' },
  ALMOST_READY: { badge: 'badge-medium', icon: 'circle-alert' },
  NOT_READY: { badge: 'badge-critical', icon: 'shield-x' },
}
const STATUS: Record<ReadinessCheck['status'], { line: string; icon: IconName; item: string }> = {
  PASS: { line: 'ok', icon: 'check-circle', item: 'is-pass' },
  WARN: { line: 'wait', icon: 'circle-alert', item: 'is-warn' },
  FAIL: { line: 'bad', icon: 'octagon-alert', item: 'is-fail' },
}
const SEVERITY_ICON: Record<string, IconName> = { CRITICAL: 'octagon-alert', HIGH: 'triangle-alert', MEDIUM: 'circle-alert', LOW: 'info' }

function money(value: Money): string {
  return value ? formatAmount(value.amount, { currency: value.currency }) : '—'
}

function checkAction(check: ReadinessCheck, t: T): { to: string; label: string } | null {
  if (check.status === 'PASS') return null
  switch (check.id) {
    case 'HISTORY':
    case 'COVERAGE':
      return { to: '/documents', label: t(`checks.${check.id}.action`) }
    case 'RECONCILED':
      return { to: check.months[0] ? `/months/${check.months[0]}` : '/months', label: t('checks.RECONCILED.action') }
    case 'REVIEW':
      return { to: '/review', label: t('checks.REVIEW.action') }
    case 'CASH':
      return { to: '/dashboard', label: t('checks.CASH.action') }
    default:
      return null
  }
}

function Check({ check }: { check: ReadinessCheck }) {
  const { t } = useTranslation(['readiness', 'risk', 'dashboard'])
  const status = STATUS[check.status]
  const action = checkAction(check, t)
  return (
    <li className={`ready-check ${status.item}`}>
      <span className={`status-line ${status.line}`}>
        <Icon name={status.icon} size="sm" />
        {t(`status.${check.status}`)}
      </span>
      <div className="ready-check-body">
        <h3>{t(`checks.${check.id}.title`)}</h3>
        <p>{checkText(check, t)}</p>
        {check.findings.length > 0 && (
          <ul className="ready-findings">
            {check.findings.map((f) => (
              <li key={f.findingId}>
                <Link className="link" to={f.link}>
                  <Icon name={SEVERITY_ICON[f.severity] ?? 'circle-alert'} size="sm" />
                  {f.month ? `${formatMonth(f.month)}: ${f.title}` : f.title}
                </Link>
                {f.nextStep && <span className="reason">{f.nextStep}</span>}
              </li>
            ))}
          </ul>
        )}
        {action && (
          <Link className="link no-print" to={action.to}>
            {action.label}
            <Icon name="chevron-right" size="sm" />
          </Link>
        )}
      </div>
    </li>
  )
}

function Figure({ label, value, note }: { label: string; value: Money | string | number; note: string }) {
  const isMoney = typeof value === 'object' && value !== null
  return (
    <div>
      <dt>{label}</dt>
      <dd className="v">
        {isMoney && <small>{value.currency}</small>}
        {isMoney ? money(value) : String(value ?? '—')}
      </dd>
      <dd className="n">{note}</dd>
    </div>
  )
}

function Report({ data }: { data: Readiness }) {
  const { t } = useTranslation(['readiness', 'risk', 'dashboard'])
  const level = LEVEL[data.level]
  const open = data.checks.filter((c) => c.status !== 'PASS').length
  const headline = data.level === 'READY' ? t('headline.READY') : t(`headline.${data.level}`, { count: open })
  const monthList = data.months.map((m) => m.month)
  const last = data.months[data.months.length - 1]
  const tot = data.totals
  const explained = data.months.filter((m) => m.explanation)
  return (
    <>
      <section className="panel ready-verdict" aria-labelledby="ready-h">
        <div className="ready-verdict-head">
          <span className={`badge ${level.badge}`}>
            <Icon name={level.icon} />
            {t(`level.${data.level}`)}
          </span>
          <h2 id="ready-h">{headline}</h2>
          <p className="small muted">
            {t('prepared', {
              workspace: data.workspace,
              period: periodText(monthList, t),
              currency: data.currency,
              framework: data.framework === 'US_GAAP' ? 'US GAAP' : 'IFRS',
              date: formatDate(data.generatedAt), // the viewer's own day, not UTC's
            })}
          </p>
        </div>
        <h3 className="ready-checks-title">{t('checksTitle')}</h3>
        <ul className="ready-checks">
          {data.checks.map((check) => (
            <Check key={check.id} check={check} />
          ))}
        </ul>
        <p className="ready-note small muted">{t('notCredit')}</p>
      </section>

      <section className="ledger ready-glance" aria-labelledby="ready-fig-h">
        <h2 id="ready-fig-h" className="type-h2">
          {t('figuresTitle')}
        </h2>
        <dl className="ledger-figures">
          <Figure label={t('figures.months')} value={tot.months} note={monthList.length ? t('figures.monthsNote', { first: formatMonth(monthList[0]), last: formatMonth(monthList[monthList.length - 1]) }) : ''} />
          <Figure label={t('figures.averageIn')} value={tot.averageIn} note={t('figures.totalNote', { total: money(tot.moneyIn) })} />
          <Figure label={t('figures.averageOut')} value={tot.averageOut} note={t('figures.totalNote', { total: money(tot.moneyOut) })} />
          <Figure label={t('figures.averageNet')} value={tot.averageNet} note={t('figures.totalNote', { total: money(tot.net) })} />
          <Figure label={t('figures.matchedShare')} value={percent(tot.matchedShare)} note={t('figures.matchedNote')} />
          <Figure label={t('figures.closing')} value={tot.closing} note={last ? t('figures.closingNote', { month: formatMonth(last.month) }) : ''} />
        </dl>
      </section>

      <section className="panel" aria-labelledby="ready-months-h">
        <div className="panel-head">
          <h2 id="ready-months-h">{t('monthsTitle')}</h2>
        </div>
        <div className="chart-table-wrap">
          <table className="data-table ready-table">
            <thead>
              <tr>
                <th>{t('columns.month')}</th>
                <th className="r">{t('columns.moneyIn')}</th>
                <th className="r">{t('columns.moneyOut')}</th>
                <th className="r hide-rt">{t('columns.net')}</th>
                <th className="r hide-rt">{t('columns.closing')}</th>
                <th className="r">{t('columns.matched')}</th>
                <th>{t('columns.risk')}</th>
              </tr>
            </thead>
            <tbody>
              {data.months.map((m) => (
                <tr key={m.month}>
                  <td>
                    <Link className="link" to={`/months/${m.month}`}>
                      {formatMonth(m.month)}
                    </Link>
                  </td>
                  <td className="r">{money(m.moneyIn)}</td>
                  <td className="r">{money(m.moneyOut)}</td>
                  <td className="r hide-rt">{money(m.net)}</td>
                  <td className="r hide-rt">{money(m.closing)}</td>
                  <td className="r">{percent(m.matchedShare)}</td>
                  <td>{m.riskLevel ? <span className={`badge badge-${m.riskLevel.toLowerCase()}`}>{t(`risk:severity.${m.riskLevel}`)}</span> : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {explained.length > 0 && (
        <section className="panel" aria-labelledby="ready-explained-h">
          <div className="panel-head">
            <div className="stack gap-1">
              <h2 id="ready-explained-h">{t('explainedTitle')}</h2>
              <p className="small muted">{t('explainedNote')}</p>
            </div>
          </div>
          <ul className="ready-explained">
            {explained.map((m) => (
              <li key={m.month}>
                <div className="row">
                  <strong>{formatMonth(m.month)}</strong>
                  {m.riskLevel && <span className={`badge badge-${m.riskLevel.toLowerCase()}`}>{t(`risk:severity.${m.riskLevel}`)}</span>}
                </div>
                <p>{m.explanation}</p>
              </li>
            ))}
          </ul>
        </section>
      )}

      <div className="ready-split">
        {data.clients.length > 0 && (
          <section className="panel" aria-labelledby="ready-clients-h">
            <div className="panel-head">
              <div className="stack gap-1">
                <h2 id="ready-clients-h">{t('clientsTitle')}</h2>
                <p className="small muted">{t('clientsNote')}</p>
              </div>
            </div>
            <ul className="ready-clients">
              {data.clients.map((c) => (
                <li key={c.name} className="hbar">
                  <span>{c.name}</span>
                  <span className="val">{percent(c.share)}</span>
                  <span className="track">
                    <i style={{ width: percent(c.share) }} /* allow-raw-style: a client's share of money in */ />
                  </span>
                </li>
              ))}
            </ul>
          </section>
        )}
        <section className="panel" aria-labelledby="ready-docs-h">
          <div className="panel-head">
            <h2 id="ready-docs-h">{t('documentsTitle')}</h2>
          </div>
          <ul className="ready-docs">
            {data.documents.map((d) => (
              <li key={d.type}>
                <Icon name={d.type === 'BANK_STATEMENT' ? 'bank' : d.type === 'RECEIPT' ? 'receipt' : d.type === 'LEDGER_EXPORT' ? 'book' : 'file-text'} size="sm" />
                {t(`documents.${d.type}`, { count: d.count })}
              </li>
            ))}
          </ul>
        </section>
      </div>
    </>
  )
}

export function ReadinessContent() {
  const { t } = useTranslation(['readiness'])
  const { data, isLoading } = useReadiness()
  const empty = !isLoading && (!data || data.months.length === 0)
  return (
    <div className="page ready-page">
      <div className="page-head">
        <div className="spread">
          <div className="stack gap-2">
            <h1 className="type-title">{t('title')}</h1>
            <p>{t('subtitle')}</p>
          </div>
          {!empty && (
            <Button variant="primary" className="no-print" onClick={() => window.print()} disabled={!data}>
              <Icon name="download" size="sm" />
              {t('print')}
            </Button>
          )}
        </div>
      </div>
      {isLoading && <p className="muted">{t('loading')}</p>}
      {empty && (
        <EmptyState
          icon={<Icon name="book" />}
          title={t('empty.title')}
          description={t('empty.body')}
          action={
            <Link className="button button-primary" to="/documents">
              {t('empty.action')}
            </Link>
          }
        />
      )}
      {data && data.months.length > 0 && <Report data={data} />}
    </div>
  )
}

export function ReadinessPage() {
  return <ReadinessContent />
}
