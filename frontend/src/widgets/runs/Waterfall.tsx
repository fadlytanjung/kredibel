/**
 * The span waterfall of one run (spec 017, AC-017-6; docs/11 §6.12): the workflow, its nodes and
 * calls on one time axis, model calls in evidence violet, code in slate, each with its duration
 * and one line of detail.
 */

import { useTranslation } from 'react-i18next'
import type { Run } from '../../entities/run'
import { seconds } from './format'
import { spanRows } from './spans'

export function Waterfall({ run, selected, onSelect }: { run: Run; selected: string | null; onSelect: (key: string) => void }) {
  const { t } = useTranslation('runs')
  const rows = spanRows(run, t)
  const total = Math.max(rows[0].end, 1)
  const ticks: number[] = []
  for (let s = 0; s * 1000 < total; s += 10) ticks.push(s)
  return (
    <div className="panel waterfall-panel">
      <div className="span-axis" aria-hidden="true">
        <span className="span-name" />
        <span className="span-track">
          {ticks.map((s) => (
            <span key={s} style={{ left: `${((s * 1000) / total) * 100}%` }} /* allow-raw-style: the tick's position on the time axis */>
              {t('detail.seconds', { seconds: s })}
            </span>
          ))}
        </span>
      </div>
      <ol className="spans">
        {rows.map((row) => {
          const left = (row.start / total) * 100
          const width = Math.max(((row.end - row.start) / total) * 100, 0.6)
          return (
            <li key={row.key} className={`span-row d${row.depth} ${row.kind}${selected === row.key ? ' sel' : ''}`}>
              <button type="button" className="span-name" onClick={() => onSelect(row.key)} aria-pressed={selected === row.key}>
                {row.name}
              </button>
              <span className="span-track">
                <i style={{ left: `${left.toFixed(2)}%`, width: `${width.toFixed(2)}%` }} /* allow-raw-style: the span's place on the time axis */ />
              </span>
              <span className="span-dur">{seconds(row.end - row.start)}</span>
              <span className="span-detail">{row.detail}</span>
            </li>
          )
        })}
      </ol>
      <p className="span-legend">
        <span className="llm">
          <i />
          {t('detail.legend.llm')}
        </span>
        <span className="code">
          <i />
          {t('detail.legend.code')}
        </span>
        <span className="node">
          <i />
          {t('detail.legend.node')}
        </span>
      </p>
    </div>
  )
}
