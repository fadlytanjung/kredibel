/**
 * The money flow as a Sankey (spec 010, T010-05, AC-010-6; docs/11 §6.2): d3-sankey places the
 * nodes, we draw the SVG with the kit's classes. Every band and node is a button that opens the
 * bank lines behind it; a band's title gives its amount and line count on hover or focus.
 */

import { useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import type { MoneyFlow } from '../../entities/insight'
import { COLUMN_OF, type LaidLink, type LaidNode, layoutFlow } from './layout'
import { type Unit, short } from './units'

export interface SankeyChartProps {
  flow: MoneyFlow
  unit: Unit
  width: number
  /** Column headings, left to right. */
  columns: string[]
  onOpen: (flowId: string, title: string) => void
}

// Label characters per drawing width; a character is up to 9.4 units at the kit's 15 px labels.
const CHARS = { 1100: { side: 30, middle: 22 }, 760: { side: 18, middle: 14 } }
const CHAR = 9.4

function clip(text: string, chars: number): string {
  return text.length > chars ? `${text.slice(0, chars - 1)}…` : text
}

/** Room for the longest label and amount of a side, never more than a third of the drawing. */
function room(labels: string[], width: number): number {
  const longest = Math.max(0, ...labels.map((l) => l.length))
  return Math.min(width / 3, Math.max(90, longest * CHAR + 16))
}

export function SankeyChart({ flow, unit, width, columns, onOpen }: SankeyChartProps) {
  const { t } = useTranslation('dashboard')
  const chars = CHARS[width as keyof typeof CHARS] ?? CHARS[760]
  const amount = (value?: { amount: string }) => (value ? short(value.amount, unit) : '')
  const sideLabel = (n: MoneyFlow['nodes'][number]) => `${clip(n.label, chars.side)} ${amount(n.value)}`
  const ends = Math.max(...flow.nodes.map((n) => COLUMN_OF[n.column]))
  const left = room(flow.nodes.filter((n) => n.column === 'SOURCE').map(sideLabel), width)
  const right = room(flow.nodes.filter((n) => COLUMN_OF[n.column] === ends).map(sideLabel), width)
  const { nodes, links, height } = useMemo(() => layoutFlow(flow, width, { left, right }), [flow, width, left, right])
  const linkName = (l: LaidLink) => {
    const source = l.source as LaidNode
    const target = l.target as LaidNode
    return t('charts.band', { source: source.flow.label, target: target.flow.label, amount: amount(l.flow.value) })
  }
  const press = (open: () => void) => (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault()
      open()
    }
  }
  const xs = [...new Set(nodes.map((n) => n.x0 ?? 0))].sort((a, b) => a - b)

  return (
    <svg
      className="chart sankey"
      viewBox={`0 0 ${width} ${height}`}
      role="group"
      aria-label={t('charts.flowAria', { sources: nodes.filter((n) => n.side === 'left').length })}
    >
      {xs.map((x, i) =>
        columns[i] ? (
          <text key={x} className="col" x={i === 0 ? x - 8 : i === xs.length - 1 ? x + 22 : x + 7} y={18} textAnchor={i === 0 ? 'end' : i === xs.length - 1 ? 'start' : 'middle'}>
            {columns[i]}
          </text>
        ) : null,
      )}
      <g>
        {links.map((l) => (
          <path
            key={l.flow.id}
            className={`band ${l.role}`}
            d={l.path}
            tabIndex={0}
            role="button"
            aria-label={`${linkName(l)}, ${t('charts.lines', { count: l.flow.lineCount ?? 0 })}`}
            onClick={() => onOpen(l.flow.id, linkName(l))}
            onKeyDown={press(() => onOpen(l.flow.id, linkName(l)))}
          >
            <title>{`${linkName(l)} · ${t('charts.lines', { count: l.flow.lineCount ?? 0 })}`}</title>
          </path>
        ))}
      </g>
      <g>
        {nodes.map((n) => {
          const x0 = n.x0 ?? 0
          const x1 = n.x1 ?? 0
          const y0 = n.y0 ?? 0
          const y1 = n.y1 ?? 0
          const label = clip(n.flow.label, n.side === 'top' ? chars.middle : chars.side)
          const value = amount(n.flow.value)
          const open = () => onOpen(n.flow.id, `${n.flow.label} ${value}`)
          return (
            <g key={n.flow.id}>
              <rect
                className={`node ${n.role}`}
                x={x0}
                y={y0}
                width={x1 - x0}
                height={Math.max(2, y1 - y0)}
                tabIndex={0}
                role="button"
                aria-label={`${n.flow.label} ${value}`}
                onClick={open}
                onKeyDown={press(open)}
              >
                <title>{`${n.flow.label} ${value}`}</title>
              </rect>
              {n.side === 'left' && (
                <text x={x0 - 8} y={(y0 + y1) / 2} dy="0.35em" textAnchor="end">
                  {label} <tspan className="amt">{value}</tspan>
                </text>
              )}
              {n.side === 'right' && (
                <text x={x1 + 8} y={(y0 + y1) / 2} dy="0.35em" textAnchor="start">
                  {label} <tspan className="amt">{value}</tspan>
                </text>
              )}
              {n.side === 'top' && (
                <text className="node-label" x={(x0 + x1) / 2} y={y0 - 8} textAnchor="middle">
                  {label} <tspan className="amt">{value}</tspan>
                </text>
              )}
            </g>
          )
        })}
      </g>
    </svg>
  )
}
