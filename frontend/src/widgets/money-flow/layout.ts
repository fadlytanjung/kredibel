/**
 * Lays out a money flow (docs/08 §5.1) with d3-sankey: positions only. Columns follow the flow's
 * own column names, so sources are always left and statement lines (or who was paid) right.
 */

import { type SankeyLink, type SankeyNode, sankey } from 'd3-sankey'
import type { FlowLink, FlowNode, MoneyFlow } from '../../entities/insight'

export const COLUMN_OF: Record<FlowNode['column'], number> = { SOURCE: 0, ACCOUNT: 1, ACTIVITY: 2, LINE: 3, USE: 2 }
const COLUMN = COLUMN_OF

export type Role = 'src' | 'acc' | 'operating' | 'investing' | 'financing' | 'kept' | 'use' | 'unclassified'

interface NodeData {
  id: string
  flow: FlowNode
}
interface LinkData {
  id: string
  flow: FlowLink
}
export type LaidNode = SankeyNode<NodeData, LinkData> & { role: Role; side: 'left' | 'right' | 'top' }
export type LaidLink = SankeyLink<NodeData, LinkData> & { role: Role; path: string }

export function roleOf(node: FlowNode): Role {
  if (node.id.endsWith(':KEPT')) return 'kept'
  if (node.column === 'SOURCE') return 'src'
  if (node.column === 'ACCOUNT') return 'acc'
  if (node.column === 'USE') return 'use'
  const cls = (node.cashflowClass ?? '').toLowerCase()
  return cls === 'operating' || cls === 'investing' || cls === 'financing' ? cls : 'unclassified'
}

/** A band as a filled shape (the kit fills bands): two curves, as wide as the link's value. */
function band(link: SankeyLink<NodeData, LinkData>): string {
  const source = link.source as SankeyNode<NodeData, LinkData>
  const target = link.target as SankeyNode<NodeData, LinkData>
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

export interface Layout {
  nodes: LaidNode[]
  links: LaidLink[]
  height: number
}

/** `width` is the drawing's own coordinate width (its viewBox); margins leave room for labels. */
export function layoutFlow(flow: MoneyFlow, width: number, margins: { left: number; right: number }): Layout {
  const perColumn = new Map<number, number>()
  for (const n of flow.nodes) perColumn.set(COLUMN[n.column], (perColumn.get(COLUMN[n.column]) ?? 0) + 1)
  const crowded = Math.max(1, ...perColumn.values())
  const height = Math.max(340, crowded * 38 + 88)
  const graph = sankey<NodeData, LinkData>()
    .nodeId((n) => n.id)
    .nodeAlign((n) => COLUMN[n.flow.column])
    .nodeWidth(14)
    .nodePadding(16)
    .nodeSort(null)
    .extent([
      [margins.left, 64],
      [width - margins.right, height - 12],
    ])({
    nodes: flow.nodes.map((n) => ({ id: n.id, flow: n })),
    links: flow.links
      .filter((l) => Number(l.value.amount) > 0)
      .map((l) => ({ id: l.id, flow: l, source: l.source, target: l.target, value: Number(l.value.amount) })),
  })
  const lastColumn = Math.max(...flow.nodes.map((n) => COLUMN[n.column]))
  const nodes = graph.nodes.map((n) => {
    const column = COLUMN[n.flow.column]
    const side: LaidNode['side'] = column === 0 ? 'left' : column === lastColumn ? 'right' : 'top'
    return Object.assign(n, { role: roleOf(n.flow), side })
  })
  const links = graph.links.map((l) => {
    const target = l.target as LaidNode
    const role: Role = target.role === 'acc' ? 'src' : target.role
    return Object.assign(l, { role, path: band(l) })
  })
  return { nodes, links, height }
}
