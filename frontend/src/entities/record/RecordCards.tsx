/** Invoices and receipts as read, each value with how it was found (spec 005, T005-03, T005-11). */

import { useTranslation } from 'react-i18next'
import { formatDate } from '../../shared/lib/formatDate'
import { formatMoney } from '../../shared/lib/formatMoney'
import { Badge } from '../../shared/ui'
import { focusOf, type Invoice, type Receipt, type ValueFocus, type ValueReading } from './api'

type Money = { amount: string; currency: string } | null | undefined

const VARIANT = { AGREED: 'clean', SINGLE_SOURCE: 'medium', CONFLICT: 'high', MISSING: 'critical' } as const

function money(value: Money): string {
  return value ? formatMoney(value.amount, { currency: value.currency }) : '—'
}

interface ValueRowProps {
  label: string
  value: string
  reading?: ValueReading
  focus?: ValueFocus
  focused?: string
  onFocus: (focus: ValueFocus) => void
}

/** A label, the value, and its reading; a value with a box can be shown on the page. */
function ValueRow({ label, value, reading, focus, focused, onFocus }: ValueRowProps) {
  const { t } = useTranslation('documents')
  const content = (
    <>
      <span className="muted">{label}</span>
      <span className="row items-center gap-2">
        <strong>{value}</strong>
        {reading && <Badge variant={VARIANT[reading.status]}>{t(`detail.readingStatus.${reading.status}`)}</Badge>}
      </span>
    </>
  )
  if (!focus) return <div className="row spread">{content}</div>
  return (
    <button
      type="button"
      className={`row spread text-left cursor-pointer ${focused === focus.key ? 'is-selected' : ''}`}
      aria-pressed={focused === focus.key}
      title={t('detail.showOnPage', { page: focus.page })}
      onClick={() => onFocus(focus)}
    >
      {content}
    </button>
  )
}

/** A field of a record: its reading key, label and display value; null hides an absent field. */
interface FieldSpec {
  field: string
  label: string
  value: string | null
}

function fieldRows(
  recordId: string,
  readings: Record<string, ValueReading>,
  fields: FieldSpec[],
  focused: string | undefined,
  onFocus: (focus: ValueFocus) => void,
) {
  return fields
    .filter((f) => f.value !== null)
    .map((f) => (
      <ValueRow
        key={f.field}
        label={f.label}
        value={f.value ?? ''}
        reading={readings[f.field]}
        focus={focusOf(recordId, f.field, readings[f.field])}
        focused={focused}
        onFocus={onFocus}
      />
    ))
}

interface CardProps<T> {
  record: T
  focused?: string
  onFocus: (focus: ValueFocus) => void
}

export function InvoiceCard({ record: inv, focused, onFocus }: CardProps<Invoice>) {
  const { t } = useTranslation('documents')
  const r = inv.readings ?? {}
  const fields: FieldSpec[] = [
    { field: 'issuerName', label: t('detail.invoice.issuer'), value: inv.issuerName || '—' },
    { field: 'buyerName', label: t('detail.invoice.buyer'), value: inv.buyerName || '—' },
    { field: 'issueDate', label: t('detail.invoice.issueDate'), value: inv.issueDate ? formatDate(inv.issueDate) : '—' },
    { field: 'dueDate', label: t('detail.invoice.dueDate'), value: inv.dueDate ? formatDate(inv.dueDate) : null },
    { field: 'subtotal', label: t('detail.invoice.subtotal'), value: money(inv.subtotal) },
    { field: 'tax', label: t('detail.invoice.tax'), value: money(inv.tax) },
    { field: 'total', label: t('detail.invoice.total'), value: money(inv.total) },
    {
      field: 'payTo',
      label: t('detail.invoice.payTo'),
      value: inv.payToMasked ? `${inv.payToBank ?? ''} ${inv.payToMasked}`.trim() : null,
    },
  ]
  return (
    <div className="card p-4 stack gap-3">
      <div className="spread items-center">
        <h3 className="type-h3">{inv.number || t('detail.invoice.untitled')}</h3>
        <Badge variant="outline">{t(`detail.invoice.kind.${inv.kind}`)}</Badge>
      </div>
      <div className="stack gap-2">{fieldRows(inv.invoiceId, r, fields, focused, onFocus)}</div>
      {(inv.lines?.length ?? 0) > 0 && (
        <div className="table-panel rt-wrap">
          <table className="data-table rt">
            <thead>
              <tr>
                <th>{t('detail.columns.description')}</th>
                <th className="r">{t('detail.invoice.qty')}</th>
                <th className="r">{t('detail.columns.amount')}</th>
                <th>{t('detail.columns.reading')}</th>
              </tr>
            </thead>
            <tbody>
              {inv.lines?.map((ln, i) => {
                const reading = r[`lines.${i}.amount`]
                const focus = focusOf(inv.invoiceId, `lines.${i}.amount`, reading)
                return (
                  <tr
                    key={i}
                    className={`${focus ? 'is-clickable' : ''} ${focus && focused === focus.key ? 'is-selected' : ''}`}
                    onClick={focus ? () => onFocus(focus) : undefined}
                  >
                    <td data-cell="wide">{ln.description}</td>
                    <td className="r">{ln.qty ?? '—'}</td>
                    <td className="r">{money(ln.amount)}</td>
                    <td>
                      {reading && (
                        <Badge variant={VARIANT[reading.status]}>{t(`detail.readingStatus.${reading.status}`)}</Badge>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
      {(inv.notes?.length ?? 0) > 0 && <p className="small muted">{inv.notes?.join(' · ')}</p>}
    </div>
  )
}

export function ReceiptCard({ record: rc, focused, onFocus }: CardProps<Receipt>) {
  const { t } = useTranslation('documents')
  const r = rc.readings ?? {}
  const when = rc.date ? `${formatDate(rc.date)}${rc.time ? ` ${rc.time}` : ''}` : '—'
  const fields: FieldSpec[] = [
    { field: 'date', label: t('detail.receipt.date'), value: when },
    { field: 'number', label: t('detail.receipt.number'), value: rc.number ?? null },
    { field: 'tax', label: t('detail.invoice.tax'), value: rc.tax ? money(rc.tax) : null },
    { field: 'total', label: t('detail.invoice.total'), value: money(rc.total) },
  ]
  return (
    <div className="card p-4 stack gap-3">
      <div className="spread items-center">
        <h3 className="type-h3">{rc.merchantName || t('detail.receipt.untitled')}</h3>
        <Badge variant="outline">{t(`detail.receipt.method.${rc.paymentMethod ?? 'UNKNOWN'}`)}</Badge>
      </div>
      <div className="stack gap-2">{fieldRows(rc.receiptId, r, fields, focused, onFocus)}</div>
      {(rc.items?.length ?? 0) > 0 && (
        <ul className="stack gap-1">
          {rc.items?.map((item, i) => (
            <li key={i} className="row spread small">
              <span>{item.description}</span>
              <span>{money(item.amount)}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
