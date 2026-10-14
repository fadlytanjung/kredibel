/**
 * Profit & Loss Interactive Flow (Sankey Chart).
 *
 * Visualizes the flow of funds:
 * Revenue Sources ➔ Total Revenue ➔ Cost of Goods Sold & Gross Profit ➔ Subledgers & Net Profit.
 * Built with d3-sankey; clicking any node or band opens its supporting ledger entries.
 */

import { useCallback, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { type SankeyLink, type SankeyNode, sankey } from 'd3-sankey'
import type { ProfitLoss } from '../../entities/profit-loss'
import { formatMoney } from '../../shared/lib/formatMoney'
import { short, unitFor } from '../../shared/lib/units'
import { SegmentedControl } from '../../shared/ui'
import { type ProfitEntryItem, ProfitLossEntriesSheet } from './ProfitLossEntriesSheet'

export interface ProfitLossFlowProps {
  report: ProfitLoss
}

interface FlowNodeData {
  id: string
  label: string
  column: number
  valueAmount: number
  role: 'src' | 'acc' | 'use' | 'kept' | 'operating'
  entries: ProfitEntryItem[]
}

interface FlowLinkData {
  id: string
  source: string
  target: string
  value: number
  role: 'src' | 'acc' | 'use' | 'kept' | 'operating'
  entries: ProfitEntryItem[]
}

type PnlSankeyNode = SankeyNode<FlowNodeData, FlowLinkData>
type PnlSankeyLink = SankeyLink<FlowNodeData, FlowLinkData>

const CHAR = 8.4

function clip(text: string, chars: number): string {
  return text.length > chars ? `${text.slice(0, chars - 1)}…` : text
}

function room(labels: string[], totalWidth: number): number {
  const longest = Math.max(0, ...labels.map((l) => l.length))
  return Math.min(totalWidth * 0.32, Math.max(140, Math.ceil(longest * CHAR + 24)))
}

function bandPath(link: PnlSankeyLink): string {
  const source = link.source as PnlSankeyNode
  const target = link.target as PnlSankeyNode
  const x0 = source.x1 ?? 0
  const x1 = target.x0 ?? 0
  const half = (link.width ?? 0) / 2
  const y0 = link.y0 ?? 0
  const y1 = link.y1 ?? 0
  const xm = (x0 + x1) / 2
  return [
    `M${x0},${y0 - half}`,
    `C${xm},${y0 - half} ${xm},${y1 - half} ${x1},${y1 - half}`,
    `L${x1},${y1 + half}`,
    `C${xm},${y1 + half} ${xm},${y0 + half} ${x0},${y0 + half}`,
    'Z',
  ].join(' ')
}

export function ProfitLossFlow({ report }: ProfitLossFlowProps) {
  const { t } = useTranslation('profitLoss')
  const [exact, setExact] = useState(false)
  const [selected, setSelected] = useState<{
    title: string
    subtitle?: string
    entries: ProfitEntryItem[]
  } | null>(null)

  const currency = report.currency || 'IDR'
  const entries = useMemo(() => report.entries || [], [report.entries])

  const graphData = useMemo(() => {
    if (entries.length === 0) return null

    // 1. Separate entries by P&L category
    const revEntries = entries.filter((e) => e.pnlLine === 'REVENUE' || e.pnlLine === 'OTHER_INCOME')
    const cogsEntries = entries.filter((e) => e.pnlLine === 'COST_OF_SALES')
    const opexEntries = entries.filter((e) => e.pnlLine === 'OPERATING_EXPENSES')
    const finEntries = entries.filter((e) => e.pnlLine === 'FINANCE_COSTS' || e.pnlLine === 'INCOME_TAX')

    // Sum helper
    const sum = (list: ProfitEntryItem[]) =>
      list.reduce((acc, e) => acc + Math.max(0, Number(e.amount) || 0), 0)

    const totalRev = sum(revEntries)
    const totalCogs = sum(cogsEntries)
    const grossProfit = Math.max(0, totalRev - totalCogs)

    // Opex grouped by subledger
    const payrollEntries = opexEntries.filter((e) => e.subledger === 'PAYROLL')
    const supplierEntries = opexEntries.filter((e) => e.subledger === 'PAYABLES')
    const generalEntries = opexEntries.filter(
      (e) => e.subledger !== 'PAYROLL' && e.subledger !== 'PAYABLES',
    )

    const payrollTotal = sum(payrollEntries)
    const supplierTotal = sum(supplierEntries)
    const generalTotal = sum(generalEntries)
    const finTotal = sum(finEntries)

    const totalExpenses = payrollTotal + supplierTotal + generalTotal + finTotal
    const netProfit = Math.max(0, grossProfit - totalExpenses)

    if (totalRev <= 0) return null

    // 2. Build Col 0 Nodes (Revenue Sources)
    const revByAccount = new Map<string, { name: string; entries: ProfitEntryItem[] }>()
    for (const e of revEntries) {
      const key = e.accountCode
      if (!revByAccount.has(key)) {
        revByAccount.set(key, { name: e.accountName, entries: [] })
      }
      revByAccount.get(key)!.entries.push(e)
    }

    const nodes: FlowNodeData[] = []
    const links: FlowLinkData[] = []

    // Col 0: Sources
    Array.from(revByAccount.entries()).forEach(([code, data]) => {
      const val = sum(data.entries)
      if (val > 0) {
        const id = `src:${code}`
        nodes.push({
          id,
          label: `${code} ${data.name}`,
          column: 0,
          valueAmount: val,
          role: 'src',
          entries: data.entries,
        })
        links.push({
          id: `link:${id}->rev`,
          source: id,
          target: 'node:rev',
          value: val,
          role: 'src',
          entries: data.entries,
        })
      }
    })

    // Col 1: Total Revenue
    nodes.push({
      id: 'node:rev',
      label: t('lines.REVENUE', { defaultValue: 'Revenue' }),
      column: 1,
      valueAmount: totalRev,
      role: 'acc',
      entries: revEntries,
    })

    // Col 2: COGS & Gross Profit
    if (totalCogs > 0) {
      nodes.push({
        id: 'node:cogs',
        label: t('lines.COST_OF_SALES', { defaultValue: 'Cost of sales' }),
        column: 2,
        valueAmount: totalCogs,
        role: 'use',
        entries: cogsEntries,
      })
      links.push({
        id: 'link:rev->cogs',
        source: 'node:rev',
        target: 'node:cogs',
        value: totalCogs,
        role: 'use',
        entries: cogsEntries,
      })
    }

    if (grossProfit > 0) {
      nodes.push({
        id: 'node:gp',
        label: t('lines.GROSS_PROFIT', { defaultValue: 'Gross profit' }),
        column: 2,
        valueAmount: grossProfit,
        role: 'acc',
        entries: [...revEntries, ...cogsEntries],
      })
      links.push({
        id: 'link:rev->gp',
        source: 'node:rev',
        target: 'node:gp',
        value: grossProfit,
        role: 'acc',
        entries: [...revEntries, ...cogsEntries],
      })

      // Col 3: From Gross Profit to Operating Expenses & Net Profit
      if (payrollTotal > 0) {
        nodes.push({
          id: 'sub:payroll',
          label: t('subledgers.PAYROLL', { defaultValue: 'Payroll' }),
          column: 3,
          valueAmount: payrollTotal,
          role: 'operating',
          entries: payrollEntries,
        })
        links.push({
          id: 'link:gp->payroll',
          source: 'node:gp',
          target: 'sub:payroll',
          value: payrollTotal,
          role: 'operating',
          entries: payrollEntries,
        })
      }

      if (supplierTotal > 0) {
        nodes.push({
          id: 'sub:payables',
          label: t('subledgers.PAYABLES', { defaultValue: 'Payables (Suppliers)' }),
          column: 3,
          valueAmount: supplierTotal,
          role: 'operating',
          entries: supplierEntries,
        })
        links.push({
          id: 'link:gp->payables',
          source: 'node:gp',
          target: 'sub:payables',
          value: supplierTotal,
          role: 'operating',
          entries: supplierEntries,
        })
      }

      if (generalTotal > 0) {
        nodes.push({
          id: 'sub:general',
          label: t('subledgers.GENERAL', { defaultValue: 'General & Admin' }),
          column: 3,
          valueAmount: generalTotal,
          role: 'operating',
          entries: generalEntries,
        })
        links.push({
          id: 'link:gp->general',
          source: 'node:gp',
          target: 'sub:general',
          value: generalTotal,
          role: 'operating',
          entries: generalEntries,
        })
      }

      if (finTotal > 0) {
        nodes.push({
          id: 'sub:finance',
          label: t('lines.FINANCE_COSTS', { defaultValue: 'Finance costs' }),
          column: 3,
          valueAmount: finTotal,
          role: 'operating',
          entries: finEntries,
        })
        links.push({
          id: 'link:gp->fin',
          source: 'node:gp',
          target: 'sub:finance',
          value: finTotal,
          role: 'operating',
          entries: finEntries,
        })
      }

      if (netProfit > 0) {
        nodes.push({
          id: 'node:net',
          label: t('lines.NET_PROFIT', { defaultValue: 'Net profit' }),
          column: 3,
          valueAmount: netProfit,
          role: 'kept',
          entries,
        })
        links.push({
          id: 'link:gp->net',
          source: 'node:gp',
          target: 'node:net',
          value: netProfit,
          role: 'kept',
          entries,
        })
      }
    }

    return { nodes, links }
  }, [entries, t])

  const unit = useMemo(
    () => unitFor(graphData?.nodes.map((n) => String(Math.round(n.valueAmount))) ?? []),
    [graphData],
  )

  const formatNodeAmount = useCallback(
    (val: number) => {
      const str = String(Math.round(val))
      if (exact) {
        return formatMoney(str, { currency, code: true })
      }
      const s = short(str, unit)
      const suffix = unit.key === 'millions' ? 'M' : unit.key === 'thousands' ? 'k' : ''
      return `${s}${suffix} ${currency}`
    },
    [exact, currency, unit],
  )

  const width = 1040

  const laidGraph = useMemo(() => {
    if (!graphData || graphData.nodes.length === 0 || graphData.links.length === 0) return null

    const crowded = Math.max(
      1,
      ...[0, 1, 2, 3].map((col) => graphData.nodes.filter((n) => n.column === col).length),
    )
    const height = Math.max(380, crowded * 56 + 100)

    const col0 = graphData.nodes.filter((n) => n.column === 0)
    const col3 = graphData.nodes.filter((n) => n.column === 3)
    const leftLabels = col0.map((n) => `${clip(n.label, 28)} ${formatNodeAmount(n.valueAmount)}`)
    const rightLabels = col3.map((n) => `${clip(n.label, 28)} ${formatNodeAmount(n.valueAmount)}`)
    const leftMargin = room(leftLabels, width)
    const rightMargin = room(rightLabels, width)

    try {
      const graph = sankey<FlowNodeData, FlowLinkData>()
        .nodeId((n) => n.id)
        .nodeAlign((n) => (n as FlowNodeData).column)
        .nodeWidth(14)
        .nodePadding(24)
        .nodeSort(null)
        .extent([
          [leftMargin, 68],
          [width - rightMargin, height - 20],
        ])({
        nodes: graphData.nodes.map((n) => ({ ...n })),
        links: graphData.links.map((l) => ({ ...l })),
      })

      return {
        nodes: graph.nodes as PnlSankeyNode[],
        links: graph.links as PnlSankeyLink[],
        height,
      }
    } catch {
      return null
    }
  }, [graphData, formatNodeAmount, width])

  if (!laidGraph) {
    return (
      <div className="p-4 muted text-center">
        <p>{t('empty')}</p>
      </div>
    )
  }

  const columns = [
    t('flowColumns.sources', { defaultValue: 'Revenue Sources' }),
    t('flowColumns.turnover', { defaultValue: 'Revenue' }),
    t('flowColumns.costs', { defaultValue: 'Costs & Margin' }),
    t('flowColumns.breakdown', { defaultValue: 'Subledgers & Net Profit' }),
  ]

  const xs = [...new Set(laidGraph.nodes.map((n) => n.x0 ?? 0))].sort((a, b) => a - b)

  const openEntries = (title: string, subtitle: string | undefined, list: ProfitEntryItem[]) => {
    setSelected({ title, subtitle, entries: list })
  }

  return (
    <div className="pnl-flow-wrapper">
      <div className="chart-head row items-center justify-between flex-wrap gap-2 mb-2">
        <p className="muted small">
          {t('flowSubtitle', {
            defaultValue:
              'From revenue sources, through gross profit, to cost of goods sold and operating expenses. Click any band to inspect subledger rows.',
          })}
        </p>
        <div className="row items-center gap-2">
          <span className="small muted">{t('unitLabel', { defaultValue: 'Amounts' })}:</span>
          <SegmentedControl
            ariaLabel={t('unitLabel', { defaultValue: 'Amounts' })}
            value={exact ? 'exact' : 'compact'}
            onChange={(key) => setExact(key === 'exact')}
            options={[
              { key: 'compact', label: t('unitCompact', { defaultValue: 'Compact' }) },
              { key: 'exact', label: t('unitExact', { defaultValue: 'Exact' }) },
            ]}
          />
        </div>
      </div>
      <div className="chart-overflow overflow-x-auto">
        <svg
          className="chart sankey"
          viewBox={`0 0 ${width} ${laidGraph.height}`}
          style={{ minWidth: '760px' }} /* allow-raw-style: minimum sankey diagram width */
          role="img"
          aria-label={t('title')}
        >
          {xs.map((x, i) =>
            columns[i] ? (
              <text
                key={x}
                className="col"
                x={i === 0 ? x - 8 : i === xs.length - 1 ? x + 22 : x + 7}
                y={22}
                textAnchor={i === 0 ? 'end' : i === xs.length - 1 ? 'start' : 'middle'}
              >
                {columns[i]}
              </text>
            ) : null,
          )}
          <g>
            {laidGraph.links.map((l) => {
              const srcNode = l.source as PnlSankeyNode
              const tgtNode = l.target as PnlSankeyNode
              const exactVal = formatMoney(String(l.value), { currency, code: true })
              const label = `${srcNode.label} ➔ ${tgtNode.label}: ${exactVal}`
              return (
                <path
                  key={l.id}
                  className={`band ${l.role}`}
                  d={bandPath(l)}
                  tabIndex={0}
                  role="button"
                  aria-label={label}
                  onClick={() => openEntries(`${srcNode.label} ➔ ${tgtNode.label}`, undefined, l.entries)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault()
                      openEntries(`${srcNode.label} ➔ ${tgtNode.label}`, undefined, l.entries)
                    }
                  }}
                >
                  <title>{`${label} · ${l.entries.length} entries`}</title>
                </path>
              )
            })}
          </g>
          <g>
            {laidGraph.nodes.map((n) => {
              const x0 = n.x0 ?? 0
              const x1 = n.x1 ?? 0
              const y0 = n.y0 ?? 0
              const y1 = n.y1 ?? 0
              const h = y1 - y0
              const isLeft = n.column === 0
              const isRight = n.column === 3
              const label = clip(n.label, isLeft || isRight ? 30 : 22)
              const amtText = formatNodeAmount(n.valueAmount)

              return (
                <g key={n.id}>
                  <rect
                    className={`node ${n.role}`}
                    x={x0}
                    y={y0}
                    width={x1 - x0}
                    height={Math.max(4, h)}
                    tabIndex={0}
                    role="button"
                    aria-label={`${n.label} ${formatMoney(String(n.valueAmount), { currency, code: true })}`}
                    onClick={() =>
                      openEntries(
                        n.label,
                        formatMoney(String(n.valueAmount), { currency, code: true }),
                        n.entries,
                      )
                    }
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault()
                        openEntries(
                          n.label,
                          formatMoney(String(n.valueAmount), { currency, code: true }),
                          n.entries,
                        )
                      }
                    }}
                  >
                    <title>{`${n.label}: ${formatMoney(String(n.valueAmount), { currency, code: true })} · ${n.entries.length} entries`}</title>
                  </rect>
                  {isLeft && (
                    <text x={x0 - 8} y={(y0 + y1) / 2} dy="0.35em" textAnchor="end">
                      <tspan className="node-label">{label}</tspan>{' '}
                      <tspan className="amt">{amtText}</tspan>
                    </text>
                  )}
                  {isRight && (
                    <text x={x1 + 8} y={(y0 + y1) / 2} dy="0.35em" textAnchor="start">
                      <tspan className="node-label">{label}</tspan>{' '}
                      <tspan className="amt">{amtText}</tspan>
                    </text>
                  )}
                  {!isLeft && !isRight && (
                    <text x={(x0 + x1) / 2} y={y0 - 8} textAnchor="middle">
                      <tspan className="node-label">{label}</tspan>{' '}
                      <tspan className="amt">{amtText}</tspan>
                    </text>
                  )}
                </g>
              )
            })}
          </g>
        </svg>
      </div>

      <div className="flow-foot">
        <div className="flow-legend" role="note" aria-label={t('title')}>
          <span className="src">
            <i aria-hidden="true" />
            {t('flowLegend.sources', { defaultValue: 'Revenue sources' })}
          </span>
          <span className="acc">
            <i aria-hidden="true" />
            {t('flowLegend.turnover', { defaultValue: 'Revenue & margin' })}
          </span>
          <span className="use">
            <i aria-hidden="true" />
            {t('flowLegend.costs', { defaultValue: 'Cost of sales' })}
          </span>
          <span className="operating">
            <i aria-hidden="true" />
            {t('flowLegend.operating', { defaultValue: 'Operating subledgers' })}
          </span>
          <span className="kept">
            <i aria-hidden="true" />
            {t('flowLegend.profit', { defaultValue: 'Net profit' })}
          </span>
        </div>
        <p className="chart-note">
          {exact
            ? t('exactAmounts', { defaultValue: 'Showing exact ledger amounts.' })
            : t('compactAmounts', {
                defaultValue: 'Amounts formatted compactly; click any node or band for itemized rows.',
              })}
        </p>
      </div>

      {selected && (
        <ProfitLossEntriesSheet
          title={selected.title}
          subtitle={selected.subtitle}
          currency={currency}
          entries={selected.entries}
          onClose={() => setSelected(null)}
        />
      )}
    </div>
  )
}
