/**
 * "Money in and out by month" and "Cash-flow statement" (spec 010, T010-05, AC-010-13, AC-010-14;
 * mock dashboard.html): plain SVG from the kit's classes, amounts in the period's unit. A month
 * with a Critical or High risk is outlined; when the balances do not add up, the waterfall is
 * replaced by a sentence naming what is missing.
 */

import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { type CashFlow, type Framework, useCashFlow } from '../../entities/insight'
import { formatMonth } from '../../shared/lib/formatDate'
import { SegmentedControl } from '../../shared/ui'
import { type Unit, shiftLeft, short, unitFor } from '../money-flow'

type Month = CashFlow['months'][number]
const HOT = ['CRITICAL', 'HIGH']
const hot = (m: Month) => (HOT.includes(m.riskLevel ?? '') ? ' is-hot' : '')
const shortMonth = (month: string) => formatMonth(month, 'short')
const SIZES = [
  { cls: 'chart-compact', width: 360 },
  { cls: 'chart-medium', width: 760 },
  { cls: 'chart-wide', width: 1100 },
]

/** For geometry only: an amount in the unit as a number. */
function n(amount: string | undefined, unit: Unit): number {
  return Number(shiftLeft(amount ?? '0', unit.shift))
}

/** A round axis top and its five steps. */
function niceTicks(max: number): number[] {
  if (max <= 0) return [0, 1]
  const raw = max / 5
  const pow = 10 ** Math.floor(Math.log10(raw))
  const step = ([1, 2, 2.5, 5, 10].find((m) => m * pow >= raw) ?? 10) * pow
  return Array.from({ length: Math.ceil(max / step) + 1 }, (_, i) => i * step)
}

function tick(value: number): string {
  return new Intl.NumberFormat(undefined, { maximumFractionDigits: 1 }).format(value)
}

function InOutBars({ months, unit, width }: { months: Month[]; unit: Unit; width: number }) {
  const { t } = useTranslation('dashboard')
  const compact = width < 600
  const left = 44
  const top = 28
  const height = compact ? 220 : 300
  const plot = height - top - 30
  const ticks = niceTicks(Math.max(...months.flatMap((m) => [n(m.in.amount, unit), n(m.out.amount, unit)]), 0))
  const top0 = ticks[ticks.length - 1]
  const y = (v: number) => top + plot - (v / top0) * plot
  const group = (width - left - 8) / Math.max(1, months.length)
  const bar = Math.min(compact ? 14 : 44, group * 0.32)
  return (
    <svg className="chart bars" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={t('charts.barsAria')}>
      {ticks.map((v) => (
        <g key={v}>
          <line className="grid" x1={left} x2={width - 8} y1={y(v)} y2={y(v)} />
          <text className="tick" x={left - 6} y={y(v)} dy="0.35em" textAnchor="end">
            {tick(v)}
          </text>
        </g>
      ))}
      {months.map((m, i) => {
        const cx = left + group * i + group / 2
        const vin = n(m.in.amount, unit)
        const vout = n(m.out.amount, unit)
        return (
          <g key={m.month}>
            <rect className={`bar in${hot(m)}`} x={cx - bar - 2} y={y(vin)} width={bar} height={Math.max(1, y(0) - y(vin))} rx={3}>
              <title>{`${formatMonth(m.month)}: ${t('charts.moneyIn')} ${short(m.in.amount, unit)}`}</title>
            </rect>
            <rect className={`bar out${hot(m)}`} x={cx + 2} y={y(vout)} width={bar} height={Math.max(1, y(0) - y(vout))} rx={3}>
              <title>{`${formatMonth(m.month)}: ${t('charts.moneyOut')} ${short(m.out.amount, unit)}`}</title>
            </rect>
            {!compact && (
              <text className="net" x={cx} y={Math.min(y(vin), y(vout)) - 8} textAnchor="middle">
                {short(m.net.amount, unit, true)}
              </text>
            )}
            <text className="tick" x={cx} y={height - 10} textAnchor="middle">
              {shortMonth(m.month)}
            </text>
          </g>
        )
      })}
    </svg>
  )
}

function NetAndBalance({ months, unit, width }: { months: Month[]; unit: Unit; width: number }) {
  const { t } = useTranslation('dashboard')
  const compact = width < 600
  const left = 44
  const right = compact ? 8 : 56
  const top = 24
  const height = compact ? 220 : 300
  const plot = height - top - 30
  const nets = months.map((m) => n(m.net.amount, unit))
  const span = Math.max(...nets.map(Math.abs), 1)
  const y = (v: number) => top + plot / 2 - (v / span) * (plot / 2)
  const closings = months.map((m) => (m.closing ? n(m.closing.amount, unit) : null))
  const known = closings.filter((c): c is number => c !== null)
  const hi = Math.max(...known, 1)
  const lo = Math.min(...known, 0)
  const yb = (v: number) => top + plot - ((v - lo) / (hi - lo || 1)) * plot
  const group = (width - left - right) / Math.max(1, months.length)
  const bar = Math.min(compact ? 18 : 48, group * 0.4)
  const points = closings
    .map((c, i) => (c === null ? null : `${left + group * i + group / 2},${yb(c)}`))
    .filter(Boolean)
    .join(' ')
  return (
    <svg className="chart bars" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={t('charts.netAria')}>
      <line className="grid" x1={left} x2={width - right} y1={y(0)} y2={y(0)} />
      {months.map((m, i) => {
        const cx = left + group * i + group / 2
        const v = nets[i]
        return (
          <g key={m.month}>
            <rect className={`net-bar${hot(m)}`} x={cx - bar / 2} y={Math.min(y(v), y(0))} width={bar} height={Math.max(1, Math.abs(y(v) - y(0)))} rx={3}>
              <title>{`${formatMonth(m.month)}: ${t('charts.net')} ${short(m.net.amount, unit, true)}`}</title>
            </rect>
            {!compact && (
              <text className="net" x={cx} y={v >= 0 ? y(v) - 8 : y(v) + 16} textAnchor="middle">
                {short(m.net.amount, unit, true)}
              </text>
            )}
            <text className="tick" x={cx} y={height - 10} textAnchor="middle">
              {shortMonth(m.month)}
            </text>
          </g>
        )
      })}
      {points && <polyline className="balance-line" points={points} />}
      {months.map((m, i) =>
        closings[i] === null ? null : (
          <circle key={m.month} className="balance-dot" cx={left + group * i + group / 2} cy={yb(closings[i] as number)} r={4}>
            <title>{`${formatMonth(m.month)}: ${t('charts.balance')} ${short(m.closing?.amount ?? '0', unit)}`}</title>
          </circle>
        ),
      )}
    </svg>
  )
}

export function MonthBarsPanel({ period, framework }: { period: string; framework?: Framework }) {
  const { t } = useTranslation('dashboard')
  const [view, setView] = useState('inout')
  const { data } = useCashFlow(period, framework)
  const months = data?.months ?? []
  if (months.length === 0) return null
  const unit = unitFor(months.flatMap((m) => [m.in.amount, m.out.amount, m.closing?.amount ?? '0']))
  const outlined = months.filter((m) => hot(m)).map((m) => formatMonth(m.month, 'long'))
  return (
    <section className="chart-panel" aria-labelledby="month-bars-h">
      <div className="chart-head">
        <div>
          <h3 id="month-bars-h">{t('charts.monthsTitle')}</h3>
          <p>{outlined.length ? t('charts.monthsSubtitleHot', { months: outlined.join(', ') }) : t('charts.monthsSubtitle')}</p>
        </div>
        <SegmentedControl
          ariaLabel={t('charts.monthsViewLabel')}
          value={view}
          onChange={setView}
          options={[
            { key: 'inout', label: t('charts.inOut') },
            { key: 'net', label: t('charts.netBalance') },
          ]}
        />
      </div>
      {SIZES.map(({ cls, width }) => (
        <div key={cls} className={cls}>
          {view === 'inout' ? <InOutBars months={months} unit={unit} width={width} /> : <NetAndBalance months={months} unit={unit} width={width} />}
        </div>
      ))}
      <div className="chart-legend">
        {view === 'inout' ? (
          <>
            <span className="in"><i />{t('charts.moneyIn')}</span>
            <span className="out"><i />{t('charts.moneyOut')}</span>
          </>
        ) : (
          <>
            <span className="net"><i />{t('charts.net')}</span>
            <span className="bal"><i />{t('charts.balance')}</span>
          </>
        )}
        <span>{t(`charts.units.${unit.key}Note`)}</span>
      </div>
    </section>
  )
}

function Waterfall({ cash, unit, width }: { cash: CashFlow; unit: Unit; width: number }) {
  const { t } = useTranslation('dashboard')
  const compact = width < 600
  const labelW = compact ? 120 : 200
  const valueW = compact ? 64 : 90
  const rowH = compact ? 34 : 40
  const activities = (['OPERATING', 'INVESTING', 'FINANCING', 'UNCLASSIFIED'] as const).filter(
    (a) => a !== 'UNCLASSIFIED' || Number(cash.byActivity.UNCLASSIFIED?.amount ?? 0) !== 0,
  )
  const opening = cash.opening?.amount ?? '0'
  const closing = cash.closing?.amount ?? '0'
  let running = n(opening, unit)
  const rows: { key: string; label: string; from: number; to: number; value: string; cls: string; signed: boolean }[] = [
    { key: 'opening', label: t('charts.opening'), from: 0, to: running, value: opening, cls: 'total', signed: false },
  ]
  for (const a of activities) {
    const amount = cash.byActivity[a]?.amount ?? '0'
    const next = running + n(amount, unit)
    rows.push({ key: a, label: t(`charts.activities.${a.toLowerCase()}`), from: running, to: next, value: amount, cls: a.toLowerCase(), signed: true })
    running = next
  }
  rows.push({ key: 'closing', label: t('charts.closing'), from: 0, to: n(closing, unit), value: closing, cls: 'total', signed: false })
  const lo = Math.min(0, ...rows.flatMap((r) => [r.from, r.to]))
  const hi = Math.max(...rows.flatMap((r) => [r.from, r.to]), 1)
  const x = (v: number) => labelW + ((v - lo) / (hi - lo)) * (width - labelW - valueW)
  const height = rows.length * rowH + 16
  return (
    <svg className="chart waterfall" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={t('charts.waterfallAria')}>
      {rows.map((r, i) => {
        const y = 8 + i * rowH
        const x0 = Math.min(x(r.from), x(r.to))
        const x1 = Math.max(x(r.from), x(r.to))
        return (
          <g key={r.key}>
            <text className="wf-label" x={labelW - 12} y={y + rowH / 2} dy="0.35em" textAnchor="end">
              {r.label}
            </text>
            <rect className={`wf ${r.cls === 'unclassified' ? 'total' : r.cls}`} x={x0} y={y + 6} width={Math.max(2, x1 - x0)} height={rowH - 14} rx={3} />
            <text className="wf-val" x={x1 + 8} y={y + rowH / 2} dy="0.35em">
              {short(r.value, unit, r.signed)}
            </text>
          </g>
        )
      })}
    </svg>
  )
}

function gapSentence(gap: NonNullable<CashFlow['gaps']>[number], t: (k: string, o?: Record<string, unknown>) => string): string {
  return t(`charts.gaps.${gap.kind}`, {
    account: gap.account ?? '',
    month: gap.month ? formatMonth(gap.month) : '',
    amount: gap.amount?.amount ?? '',
  })
}

export function WaterfallPanel({ period, framework }: { period: string; framework?: Framework }) {
  const { t } = useTranslation('dashboard')
  const { data: cash } = useCashFlow(period, framework)
  if (!cash || cash.months.length === 0) return null
  // No statement in the period printed a balance (gap NO_BALANCES): opening and closing are null.
  const anchored = cash.opening !== null && cash.closing !== null
  const unit = unitFor([cash.opening?.amount ?? '0', cash.closing?.amount ?? '0', ...Object.values(cash.byActivity).map((m) => m?.amount ?? '0')])
  return (
    <section className="chart-panel" aria-labelledby="waterfall-h">
      <div className="chart-head">
        <div>
          <h3 id="waterfall-h">{t('charts.waterfallTitle')}</h3>
          <p>{t('charts.waterfallSubtitle', { framework: cash.framework === 'US_GAAP' ? 'US GAAP' : 'IFRS' })}</p>
        </div>
        <Link className="link" to="/months/all">
          {t('charts.byMonth')}
        </Link>
      </div>
      {cash.balanced === false || !anchored ? (
        <div className="p-5 stack gap-2">
          <p>{t('charts.notBalanced')}</p>
          <ul className="muted small stack gap-1">
            {(cash.gaps ?? []).map((g, i) => (
              <li key={`${g.kind}-${g.month}-${i}`}>{gapSentence(g, t)}</li>
            ))}
          </ul>
        </div>
      ) : (
        SIZES.map(({ cls, width }) => (
          <div key={cls} className={cls}>
            <Waterfall cash={cash} unit={unit} width={width} />
          </div>
        ))
      )}
      <div className="chart-legend">
        <span>{t(`charts.units.${unit.key}Note`)}</span>
      </div>
    </section>
  )
}
