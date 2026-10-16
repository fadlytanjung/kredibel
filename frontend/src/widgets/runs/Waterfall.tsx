/**
 * The span waterfall of one run (spec 017, AC-017-6; docs/11 §6.12): the workflow, its nodes and
 * calls on one time axis, model calls in evidence violet, code steps in slate (class `tool`, as
 * `.code` is the kit's condensed text), each with its duration
 * and one line of detail. The axis has about five ticks whatever the run's length.
 */

import { useTranslation } from 'react-i18next'
import { seconds, tickStep } from './format'
import type { SpanRow } from './spans'

export function Waterfall({ rows, selected, onSelect }: { rows: SpanRow[]; selected: string | null; onSelect: (key: string) => void }) {
  const { t } = useTranslation('runs')
  const total = Math.max(rows[0]?.end ?? 0, 1)
  const step = tickStep(total)
  const ticks: number[] = []
  for (let s = 0; s * 1000 < total; s += step) ticks.push(s)
  const tick = (s: number) => (step >= 60 ? t('detail.minutes', { minutes: s / 60 }) : t('detail.seconds', { seconds: s }))
  return (
    <div className="panel waterfall-panel">
      <div className="span-axis" aria-hidden="true">
        <span className="span-name" />
        <span className="span-track">
          {ticks.map((s) => (
            <span key={s} style={{ left: `${((s * 1000) / total) * 100}%` }} /* allow-raw-style: the tick's position on the time axis */>
              {tick(s)}
            </span>
          ))}
        </span>
      </div>
      <ol className="spans">
        {rows.map((row) => {
          const left = (row.start / total) * 100
          const width = Math.max(((row.end - row.start) / total) * 100, 0.6)
          return (
            <li key={row.key} className={`span-row d${row.depth} ${row.kind === 'code' ? 'tool' : row.kind}${selected === row.key ? ' sel' : ''}`}>
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
        <span className="tool">
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
