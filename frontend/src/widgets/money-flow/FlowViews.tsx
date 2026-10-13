/**
 * The money flow's other drawings (spec 010, T010-05, AC-010-7, AC-010-12): the statement lines
 * as bars grouped by activity, the links as a table (the accessible alternative), and on phones
 * the sources and uses as two lists.
 */

import { useTranslation } from 'react-i18next'
import type { FlowNode, MoneyFlow } from '../../entities/insight'
import { DataTable, type DataTableColumn } from '../../shared/ui'
import { roleOf } from './layout'
import { type Unit, short } from './units'

const ACTIVITIES = ['operating', 'investing', 'financing', 'unclassified', 'kept'] as const
const MONEY_IN = 'in'
const MONEY_OUT = 'out'

function amountOf(node: FlowNode): string {
  return node.value?.amount ?? '0'
}

function share(part: string, whole: string): string {
  const w = Number(whole)
  return `${w > 0 ? Math.min(100, Math.max(1, (Number(part) / w) * 100)) : 0}%`
}

/** Statement lines (or who was paid) grouped by activity, as horizontal bars. */
export function StatementBars({ flow, unit, onOpen }: { flow: MoneyFlow; unit: Unit; onOpen: (id: string, title: string) => void }) {
  const { t } = useTranslation('dashboard')
  const ends = flow.nodes.filter((n) => n.column === 'LINE' || n.column === 'USE')
  const largest = ends.reduce((m, n) => (Number(amountOf(n)) > Number(m) ? amountOf(n) : m), '0')
  const groups = ACTIVITIES.map((role) => ({
    role,
    nodes: ends
      .filter((n) => (roleOf(n) === 'use' ? 'operating' : roleOf(n)) === role)
      .sort((a, b) => Number(amountOf(b)) - Number(amountOf(a))),
  })).filter((g) => g.nodes.length > 0)
  return (
    <div className="hbars">
      {groups.map((g) => (
        <section key={g.role} className="hbar-group" aria-label={t(`charts.activities.${g.role}`)}>
          <h3>{t(`charts.activities.${g.role}`)}</h3>
          <ul>
            {g.nodes.map((n) => (
              <li key={n.id} className={`hbar ${g.role}`}>
                <button type="button" className="link text-left" onClick={() => onOpen(n.id, n.label)}>
                  {n.label}
                </button>
                <span className="val">{short(amountOf(n), unit)}</span>
                <span className="track">
                  <i style={{ width: share(amountOf(n), largest) }} /* allow-raw-style: a bar's share of the largest */ />
                </span>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  )
}

interface Row {
  id: string
  source: string
  target: string
  amount: string
  count: number
}

/** Every link with source, target, amount and lines (NFR-08). */
export function FlowTable({ flow, unit, onOpen }: { flow: MoneyFlow; unit: Unit; onOpen: (id: string, title: string) => void }) {
  const { t } = useTranslation('dashboard')
  const label = new Map(flow.nodes.map((n) => [n.id, n.label]))
  const rows: Row[] = flow.links.map((l) => ({
    id: l.id,
    source: label.get(l.source) ?? l.source,
    target: label.get(l.target) ?? l.target,
    amount: l.value.amount,
    count: l.lineCount ?? 0,
  }))
  const columns: DataTableColumn<Row>[] = [
    { key: 'source', header: t('charts.table.from'), sortable: true, sortValue: (r) => r.source, render: (r) => r.source },
    { key: 'target', header: t('charts.table.to'), sortable: true, sortValue: (r) => r.target, render: (r) => r.target },
    {
      key: 'amount',
      header: t(`charts.units.${unit.key}`),
      align: 'right',
      sortable: true,
      sortValue: (r) => Number(r.amount),
      render: (r) => short(r.amount, unit),
    },
    { key: 'count', header: t('charts.table.lines'), align: 'right', hideOnMobile: true, sortable: true, sortValue: (r) => r.count, render: (r) => r.count },
  ]
  return (
    <div className="chart-table-wrap">
      <DataTable
        data={[...rows].sort((a, b) => Number(b.amount) - Number(a.amount))}
        columns={columns}
        getRowKey={(r) => r.id}
        searchable
        searchPlaceholder={t('charts.table.search')}
        searchPredicate={(r, q) => `${r.source} ${r.target}`.toLowerCase().includes(q)}
        onRowClick={(r) => onOpen(r.id, `${r.source} → ${r.target}`)}
        tableClassName="chart-table"
      />
    </div>
  )
}

/** Phones: where the money came from and where it went, as two lists of bars. */
export function FlowList({ flow, unit, onOpen }: { flow: MoneyFlow; unit: Unit; onOpen: (id: string, title: string) => void }) {
  const { t } = useTranslation('dashboard')
  const sources = flow.nodes.filter((n) => n.column === 'SOURCE').sort((a, b) => Number(amountOf(b)) - Number(amountOf(a)))
  const uses = flow.nodes.filter((n) => n.column === 'LINE' || n.column === 'USE').sort((a, b) => Number(amountOf(b)) - Number(amountOf(a)))
  const largest = [...sources, ...uses].reduce((m, n) => (Number(amountOf(n)) > Number(m) ? amountOf(n) : m), '0')
  const list = (title: string, nodes: FlowNode[], cls: string) => (
    <section aria-label={title}>
      <h3>{title}</h3>
      {nodes.map((n) => (
        <button key={n.id} type="button" className={`flow-row ${roleOf(n) === 'kept' ? 'kept' : cls} w-full text-left`} onClick={() => onOpen(n.id, n.label)}>
          <span>{n.label}</span>
          <span className="amt">{short(amountOf(n), unit)}</span>
          <span className="bar">
            <i style={{ width: share(amountOf(n), largest) }} /* allow-raw-style: a row's share of the largest */ />
          </span>
        </button>
      ))}
    </section>
  )
  return (
    <div className="flow-list">
      {list(t('charts.cameFrom'), sources, MONEY_IN)}
      {list(t('charts.wentTo'), uses, MONEY_OUT)}
    </div>
  )
}
