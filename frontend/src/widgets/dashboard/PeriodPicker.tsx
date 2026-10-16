/**
 * The dashboard's period (spec 010, AC-010-1; docs/11 §6.2): Month, Range or Year. A month steps
 * with the arrows or the list; a range picks its first and last month, at most 12 months; a year is
 * one list. Nothing after today is offered.
 */

import { useTranslation } from 'react-i18next'
import { formatMonth } from '../../shared/lib/formatDate'
import { Icon, SegmentedControl } from '../../shared/ui'
import {
  addMonths,
  clampRange,
  MAX_RANGE_MONTHS,
  monthIndex,
  monthOptions,
  type PeriodKind,
  type PeriodParts,
  switchKind,
  yearOptions,
} from './period'

export function PeriodPicker({ value, onChange, dataMonths, current }: { value: PeriodParts; onChange: (next: PeriodParts) => void; dataMonths: string[]; current: string }) {
  const { t } = useTranslation('dashboard')
  const months = monthOptions(dataMonths, current)
  const latest = months[0]
  const earliest = months[months.length - 1]
  const kinds: PeriodKind[] = ['month', 'range', 'year']
  const label = (m: string) => formatMonth(m, 'longYear')
  const toOptions = months.filter((m) => monthIndex(m) >= monthIndex(value.from) && monthIndex(m) - monthIndex(value.from) < MAX_RANGE_MONTHS)

  return (
    <div className="period-picker">
      <SegmentedControl
        ariaLabel={t('periods.label')}
        value={value.kind}
        onChange={(kind) => onChange(switchKind(value, kind as PeriodKind, current))}
        options={kinds.map((kind) => ({ key: kind, label: t(`periods.kinds.${kind}`) }))}
      />
      {value.kind === 'month' && (
        <div className="period-fields">
          <button
            type="button"
            className="icon-button icon-button-sm"
            aria-label={t('periods.previousMonth')}
            disabled={value.from === earliest}
            onClick={() => onChange({ kind: 'month', from: addMonths(value.from, -1), to: addMonths(value.from, -1) })}
          >
            <Icon name="chevron-left" size="sm" />
          </button>
          <select className="select select-sm" aria-label={t('periods.month')} value={value.from} onChange={(e) => onChange({ kind: 'month', from: e.target.value, to: e.target.value })}>
            {months.map((m) => (
              <option key={m} value={m}>
                {label(m)}
              </option>
            ))}
          </select>
          <button
            type="button"
            className="icon-button icon-button-sm"
            aria-label={t('periods.nextMonth')}
            disabled={value.from === latest}
            onClick={() => onChange({ kind: 'month', from: addMonths(value.from, 1), to: addMonths(value.from, 1) })}
          >
            <Icon name="chevron-right" size="sm" />
          </button>
        </div>
      )}
      {value.kind === 'range' && (
        <div className="period-fields">
          <select className="select select-sm" aria-label={t('periods.from')} value={value.from} onChange={(e) => onChange(clampRange(e.target.value, value.to, latest))}>
            {months.map((m) => (
              <option key={m} value={m}>
                {label(m)}
              </option>
            ))}
          </select>
          <span className="muted small">{t('periods.to')}</span>
          <select className="select select-sm" aria-label={t('periods.toLabel')} value={value.to} onChange={(e) => onChange(clampRange(value.from, e.target.value, latest))}>
            {toOptions.map((m) => (
              <option key={m} value={m}>
                {label(m)}
              </option>
            ))}
          </select>
        </div>
      )}
      {value.kind === 'range' && <span className="muted small period-hint">{t('periods.rangeHint', { count: MAX_RANGE_MONTHS })}</span>}
      {value.kind === 'year' && (
        <div className="period-fields">
          <select className="select select-sm" aria-label={t('periods.year')} value={value.from.slice(0, 4)} onChange={(e) => onChange({ kind: 'year', from: `${e.target.value}-01`, to: `${e.target.value}-12` })}>
            {yearOptions(dataMonths, current).map((y) => (
              <option key={y} value={y}>
                {y}
              </option>
            ))}
          </select>
        </div>
      )}
    </div>
  )
}
