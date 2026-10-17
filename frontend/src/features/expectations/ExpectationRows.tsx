/** Spec 024, AC-024-4: the months a person expects money in and out for, one row each. */
import { useTranslation } from 'react-i18next'
import { Icon } from '../../shared/ui'
import { formatMonth } from '../../shared/lib/formatDate'

export interface ExpectationRow {
  month: string
  moneyIn: string
  moneyOut: string
}

export function ExpectationRows({ rows, currency, onChange }: { rows: ExpectationRow[]; currency: string; onChange: (rows: ExpectationRow[]) => void }) {
  const { t } = useTranslation('onboarding')
  const set = (i: number, patch: Partial<ExpectationRow>) => onChange(rows.map((row, n) => (n === i ? { ...row, ...patch } : row)))
  return (
    <div className="expect-rows">
      <p className="hint">{t('welcome.form.hint', { currency })}</p>
      {rows.map((row, i) => (
        <div className="expect-row" key={i} role="group" aria-label={t('welcome.form.rowAria', { index: i + 1 })}>
          <div className="field">
            <label htmlFor={`exp-month-${i}`}>{t('welcome.form.month')}</label>
            <input className="input" id={`exp-month-${i}`} type="month" value={row.month} onChange={(e) => set(i, { month: e.target.value })} />
          </div>
          <div className="field">
            <label htmlFor={`exp-in-${i}`}>{t('welcome.form.moneyIn')}</label>
            <input className="input n" id={`exp-in-${i}`} inputMode="numeric" value={row.moneyIn} onChange={(e) => set(i, { moneyIn: e.target.value })} />
          </div>
          <div className="field">
            <label htmlFor={`exp-out-${i}`}>{t('welcome.form.moneyOut')}</label>
            <input className="input n" id={`exp-out-${i}`} inputMode="numeric" value={row.moneyOut} onChange={(e) => set(i, { moneyOut: e.target.value })} />
          </div>
          {rows.length > 1 && (
            <button
              type="button"
              className="button button-quiet button-sm expect-remove"
              aria-label={t('welcome.form.remove', { month: row.month ? formatMonth(row.month) : i + 1 })}
              onClick={() => onChange(rows.filter((_, n) => n !== i))}
            >
              <Icon name="x" size="sm" />
            </button>
          )}
        </div>
      ))}
    </div>
  )
}
