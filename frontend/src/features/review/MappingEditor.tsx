/**
 * The column mapping of a ledger export (spec 005, T005-11, AC-005-11; docs/11 §6.5; mock
 * review-mapping.html): which column of the file holds each field, how the amounts are laid out,
 * the date format and the decimal separator, and the first rows as the mapping reads them.
 * The person confirms once per layout; code parses every row afterwards (AC-005-12).
 */

import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import type { LedgerMapping, LedgerMappingView } from '../../entities/document'
import { formatAmount } from '../../shared/lib/formatMoney'
import { formatDate } from '../../shared/lib/formatDate'
import { DATE_FORMATS } from './mapping'

type Field = 'date' | 'description' | 'accountCode' | 'accountName' | 'reference' | 'debit' | 'credit' | 'amount'
type Layout = 'debitCredit' | 'amount'

const FIELDS: Field[] = ['date', 'description', 'accountCode', 'accountName', 'reference']
const REQUIRED: Field[] = ['date', 'description', 'accountCode']

export interface MappingEditorProps {
  view: LedgerMappingView
  value: LedgerMapping
  onChange: (mapping: LedgerMapping) => void
  disabled?: boolean
  /** Rows the last mapping could not read (AC-005-12), when the item reopened. */
  badRows?: number[]
}

export function MappingEditor({ view, value, onChange, disabled, badRows = [] }: MappingEditorProps) {
  const { t } = useTranslation('review')
  const [layout, setLayout] = useState<Layout>(value.amount ? 'amount' : 'debitCredit')
  const set = (patch: Partial<LedgerMapping>) => onChange({ ...value, ...patch })
  const amountFields: Field[] = layout === 'amount' ? ['amount'] : ['debit', 'credit']
  const first = view.sampleRows[0]?.raw ?? []
  const rawOf = (column: string | null | undefined) => (column && view.header.includes(column) ? first[view.header.indexOf(column)] : '')

  const columnSelect = (field: Field) => (
    <select
      className="input"
      aria-label={t(`mapping.fields.${field}`)}
      value={value[field] ?? ''}
      disabled={disabled}
      onChange={(event) => set({ [field]: event.target.value || null })}
    >
      <option value="">{t('mapping.notInFile')}</option>
      {view.header.map((column) => (
        <option key={column} value={column}>
          {column}
        </option>
      ))}
    </select>
  )

  const chooseLayout = (next: Layout) => {
    setLayout(next)
    if (next === 'amount') set({ debit: null, credit: null, signConvention: value.signConvention ?? 'DEBIT_POSITIVE' })
    else set({ amount: null, signConvention: null })
  }

  const mapped = new Set([value.date, value.description, value.accountCode, value.accountName, value.reference, value.debit, value.credit, value.amount].filter(Boolean))

  return (
    <div className="mapping stack gap-4">
      <p className="muted small">{t('mapping.intro')}</p>
      {badRows.length > 0 && (
        <p className="banner banner-critical text-sm" role="status">
          {t('mapping.badRows', { count: badRows.length })}
        </p>
      )}

      <div className="table-panel">
        <table className="data-table mapping-fields">
          <thead>
            <tr>
              <th scope="col">{t('mapping.field')}</th>
              <th scope="col">{t('mapping.column')}</th>
              <th scope="col" className="hide-rt">
                {t('mapping.sampleRaw')}
              </th>
            </tr>
          </thead>
          <tbody>
            {[...FIELDS, ...amountFields].map((field) => (
              <tr key={field}>
                <th scope="row">
                  {t(`mapping.fields.${field}`)}
                  {REQUIRED.includes(field) || amountFields.includes(field) ? ' *' : ''}
                </th>
                <td>{columnSelect(field)}</td>
                <td className="muted small hide-rt">{rawOf(value[field])}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="row">
        <fieldset className="field m-0">
          <legend className="label">{t('mapping.layout')}</legend>
          <div className="row">
            <label className="row">
              <input type="radio" name="mapping-layout" checked={layout === 'debitCredit'} disabled={disabled} onChange={() => chooseLayout('debitCredit')} />
              {t('mapping.layoutDebitCredit')}
            </label>
            <label className="row">
              <input type="radio" name="mapping-layout" checked={layout === 'amount'} disabled={disabled} onChange={() => chooseLayout('amount')} />
              {t('mapping.layoutAmount')}
            </label>
          </div>
        </fieldset>
        {layout === 'amount' && (
          <label className="field m-0">
            <span className="label">{t('mapping.signConvention')}</span>
            <select
              className="input"
              value={value.signConvention ?? 'DEBIT_POSITIVE'}
              disabled={disabled}
              onChange={(event) => set({ signConvention: event.target.value as LedgerMapping['signConvention'] })}
            >
              <option value="DEBIT_POSITIVE">{t('mapping.DEBIT_POSITIVE')}</option>
              <option value="CREDIT_POSITIVE">{t('mapping.CREDIT_POSITIVE')}</option>
            </select>
          </label>
        )}
        <label className="field m-0">
          <span className="label">{t('mapping.dateFormat')}</span>
          <select className="input" value={value.dateFormat} disabled={disabled} onChange={(event) => set({ dateFormat: event.target.value })}>
            {DATE_FORMATS.map((format) => (
              <option key={format} value={format}>
                {format}
              </option>
            ))}
          </select>
        </label>
        <label className="field m-0">
          <span className="label">{t('mapping.decimalSeparator')}</span>
          <select
            className="input"
            value={value.decimalSeparator}
            disabled={disabled}
            onChange={(event) => set({ decimalSeparator: event.target.value as LedgerMapping['decimalSeparator'] })}
          >
            <option value=".">{t('mapping.separatorDot')}</option>
            <option value=",">{t('mapping.separatorComma')}</option>
          </select>
        </label>
      </div>

      <section className="stack gap-2" aria-label={t('mapping.sample')}>
        <h3 className="type-h3">{t('mapping.sample')}</h3>
        <div className="table-panel rt-wrap">
          <table className="data-table mapping-sample">
            <thead>
              <tr>
                {view.header.map((column) => (
                  <th key={column} scope="col" className={mapped.has(column) ? 'is-mapped' : undefined}>
                    {column}
                  </th>
                ))}
                <th scope="col">{t('mapping.sampleRead')}</th>
              </tr>
            </thead>
            <tbody>
              {view.sampleRows.map((row, index) => (
                <tr key={index}>
                  {row.raw.map((cell, cellIndex) => (
                    <td key={cellIndex} className={mapped.has(view.header[cellIndex]) ? 'is-mapped' : 'muted'}>
                      {cell}
                    </td>
                  ))}
                  <td className="small">
                    {row.parsed ? (
                      <>
                        {formatDate(row.parsed.date ?? '')} · {row.parsed.accountCode} ·{' '}
                        {row.parsed.debit && Number(row.parsed.debit.amount) ? `${t('mapping.fields.debit')} ${formatAmount(row.parsed.debit.amount)}` : ''}
                        {row.parsed.credit && Number(row.parsed.credit.amount) ? `${t('mapping.fields.credit')} ${formatAmount(row.parsed.credit.amount)}` : ''}
                      </>
                    ) : (
                      <span className="sev-high">{t('mapping.sampleUnread', { reason: row.error ?? '' })}</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
