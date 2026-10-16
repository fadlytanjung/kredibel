/** Signed reporting rows and a positive-flow presentation of the exact report totals. */
import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import type { ProfitLoss } from '../../entities/profit-loss'
import { formatMoney } from '../../shared/lib/formatMoney'
import { short, unitFor } from '../../shared/lib/units'
import { SegmentedControl } from '../../shared/ui'
import { profitFlow, type ProfitNode } from './flowData'
import { ProfitLossEntriesSheet } from './ProfitLossEntriesSheet'

export function ProfitLossFlow({ report }: { report: ProfitLoss }) {
  const { t } = useTranslation('profitLoss')
  const [exact, setExact] = useState(false)
  const [selected, setSelected] = useState<ProfitNode | null>(null)
  const graph = useMemo(() => profitFlow(report, t), [report, t])
  const unit = unitFor(report.lines.map((line) => line.amount ?? '0'))
  const money = (amount: string) => formatMoney(amount, { currency: report.currency, code: true })
  const display = (amount: string) => exact ? money(amount) : `${short(amount, unit)}${unit.key === 'millions' ? ' M' : unit.key === 'thousands' ? ' k' : ''} ${report.currency}`
  const max = Math.max(1, ...report.lines.map((line) => Math.abs(Number(line.amount))))
  const signedRows = <div className="pnl-bars">{report.lines.map((line) => <button className="pnl-row pnl-source-button" key={line.id} onClick={() => setSelected({ id: line.id, label: t(`lines.${line.id}`), amount: line.amount ?? '0', role: 'acc', entries: report.entries.filter((entry) => line.entryIds.includes(entry.entryId)) })}>
    <span>{t(`lines.${line.id}`)}</span><strong className="num">{line.amount === null ? t('unavailableAmount') : money(line.amount)}</strong>
    <span className="pnl-track" aria-hidden="true"><span className="pnl-bar" style={{ width: `${Math.abs(Number(line.amount)) / max * 100}%` }} /* allow-raw-style: chart geometry */ /></span>
  </button>)}</div>

  const draw = () => {
    if (!graph) return null
    // Only geometry is floating point; all labels and selected values retain decimal strings.
    const total = Number(graph.income.amount)
    const span = Math.max(354, (Math.max(graph.sources.length, graph.uses.length) - 1) * 40 + 120)
    const gap = 40
    const available = Math.max(120, span - (Math.max(graph.sources.length, graph.uses.length) - 1) * gap)
    const k = available / total
    const centerY = 80 + (span - available) / 2
    const height = Math.max(500, available + Math.max(graph.sources.length, graph.uses.length) * gap + 100)
    const parts: React.ReactNode[] = []
    const node = (item: ProfitNode, x: number, y: number, h: number, side: 'left' | 'right' | 'center') => {
      const labelX = side === 'left' ? x - 8 : side === 'right' ? x + 22 : x + 7
      const anchor = side === 'left' ? 'end' : side === 'right' ? 'start' : 'middle'
      const labelY = side === 'center' ? y - 26 : y + h / 2
      return <g key={item.id}>
        <rect className={`node ${item.role}`} x={x} y={y} width={14} height={Math.max(2, h)} tabIndex={0} role="button" aria-label={`${item.label} ${money(item.amount)}`} onClick={() => setSelected(item)} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setSelected(item) } }}><title>{`${item.label}: ${money(item.amount)}`}</title></rect>
        <text x={labelX} y={labelY} textAnchor={anchor}><tspan>{item.label.length > 28 ? `${item.label.slice(0, 27)}…` : item.label}</tspan><tspan className="amt" x={labelX} dy={18}>{display(item.amount)}</tspan></text>
      </g>
    }
    for (const [items, side] of [[graph.sources, 'left'], [graph.uses, 'right']] as const) {
      let y = 80 + (span - (available + (items.length - 1) * gap)) / 2
      let center = centerY
      for (const item of items) {
        const h = Number(item.amount) * k
        const [x0, x1, y0, y1] = side === 'left' ? [254, 513, y, center] : [527, 780, center, y]
        const mid = (x0 + x1) / 2
        const path = `M${x0},${y0} C${mid},${y0} ${mid},${y1} ${x1},${y1} L${x1},${y1+h} C${mid},${y1+h} ${mid},${y0+h} ${x0},${y0+h} Z`
        parts.push(<path key={`band:${item.id}`} className={`band ${item.role}`} d={path} role="button" tabIndex={0} aria-label={t('bandLabel', { label: item.label, amount: money(item.amount) })} onClick={() => setSelected(item)} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setSelected(item) } }}><title>{`${item.label}: ${money(item.amount)}`}</title></path>)
        parts.push(node(item, side === 'left' ? 240 : 780, y, h, side))
        y += h + gap
        center += h
      }
    }
    parts.push(node(graph.income, 513, centerY, available, 'center'))
    return <svg className="chart sankey" viewBox={`0 0 1040 ${height}`} role="group" aria-label={t('title')}>
      <text className="col" x={240} y={22} textAnchor="end">{t(graph.loss ? 'flowColumns.sourcesLoss' : 'flowColumns.sources')}</text>
      <text className="col" x={520} y={22} textAnchor="middle">{graph.income.label}</text>
      <text className="col" x={794} y={22}>{t(graph.loss ? 'flowColumns.breakdownLoss' : 'flowColumns.breakdown')}</text>
      {parts}
    </svg>
  }

  return <div className="pnl-flow-wrapper stack gap-3">
    <div className="chart-head"><p className="muted small">{t(graph?.loss ? 'flowSubtitleLoss' : 'flowSubtitle')}</p>{graph && <SegmentedControl ariaLabel={t('unitLabel')} value={exact ? 'exact' : 'compact'} onChange={(value) => setExact(value === 'exact')} options={[{ key: 'compact', label: t('unitCompact') }, { key: 'exact', label: t('unitExact') }]} />}</div>
    {graph ? <><div className="pnl-flow-wide">{draw()}</div><div className="pnl-flow-compact">{signedRows}</div></> : <><p className="muted small">{t('signedFlow')}</p>{signedRows}</>}
    {graph && <p className="chart-note">{t(exact ? 'exactAmounts' : 'compactAmounts')}</p>}
    {selected && <ProfitLossEntriesSheet title={selected.label} subtitle={money(selected.amount)} currency={report.currency} basis={report.basis} entries={selected.entries} onClose={() => setSelected(null)} />}
  </div>
}
