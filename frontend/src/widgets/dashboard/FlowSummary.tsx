/**
 * Where the money went, in short: the period's three largest sources and uses as ranked bars
 * (spec 010, T010-04; the phone drawing of the money flow, docs/11 §6.2). The full chart is T010-05.
 */

import { useTranslation } from 'react-i18next'
import type { FlowNode } from '../../entities/insight'
import { formatAmount } from '../../shared/lib/formatMoney'

function Row({ node, max, out }: { node: FlowNode; max: number; out?: boolean }) {
  const amount = node.value?.amount ?? '0'
  const width = max > 0 ? `${((Number(amount) / max) * 100).toFixed(1)}%` : '0%'
  return (
    <div className={`flow-row${out ? ' out' : ''}`}>
      <span>{node.label}</span>
      <span className="amt">{formatAmount(amount, { currency: node.value?.currency })}</span>
      <span className="bar">
        <i style={{ width }} /* allow-raw-style: share of the largest flow */ />
      </span>
    </div>
  )
}

export function FlowSummary({ sources, uses }: { sources: FlowNode[]; uses: FlowNode[] }) {
  const { t } = useTranslation('dashboard')
  const max = Math.max(0, ...[...sources, ...uses].map((n) => Number(n.value?.amount ?? 0)))
  return (
    <section className="panel" aria-labelledby="dash-flow-h">
      <div className="panel-head">
        <h2 id="dash-flow-h">{t('flowTitle')}</h2>
      </div>
      {sources.length + uses.length === 0 ? (
        <p className="muted small panel-pad">{t('noFlow')}</p>
      ) : (
        <div className="stack gap-4 panel-pad">
          <div>
            <h3 className="small muted">{t('flowIn')}</h3>
            {sources.map((n) => (
              <Row key={n.id} node={n} max={max} />
            ))}
          </div>
          <div>
            <h3 className="small muted">{t('flowOut')}</h3>
            {uses.map((n) => (
              <Row key={n.id} node={n} max={max} out />
            ))}
          </div>
        </div>
      )}
    </section>
  )
}
