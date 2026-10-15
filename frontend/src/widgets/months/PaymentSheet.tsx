/**
 * Confirm a payment by hand (spec 007, T007-10c, AC-007-16; ADR-025): amount, date, method and
 * reason, recorded as a decision with no bank evidence. It never changes bank cash totals; a
 * smaller amount leaves a partial payment.
 */

import { type FormEvent, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useCreateDecision } from '../../entities/decision'
import { Button, Icon } from '../../shared/ui'
import { rowTitle, type Row } from '../month'

const METHODS = ['TRANSFER', 'CASH', 'CARD', 'CHEQUE', 'OTHER'] as const
type Method = (typeof METHODS)[number]

export function PaymentSheet({
  row,
  currency,
  onClose,
  onConfirmed,
}: {
  row: Row
  currency: string
  onClose: () => void
  onConfirmed: () => void
}) {
  const { t } = useTranslation(['months', 'common'])
  const create = useCreateDecision()
  const [amount, setAmount] = useState(row.outstanding?.amount ?? row.total?.amount ?? '')
  const [paidOn, setPaidOn] = useState(new Date().toISOString().slice(0, 10))
  const [method, setMethod] = useState<Method>('TRANSFER')
  const [reason, setReason] = useState('')
  const [error, setError] = useState('')
  const ready = amount.trim() !== '' && paidOn !== '' && reason.trim().length >= 3 && !create.isPending

  const submit = (e: FormEvent) => {
    e.preventDefault()
    if (!ready) return
    create.mutate(
      {
        kind: 'PAYMENT_CONFIRMATION',
        ...(row.kind === 'RECEIPT' ? { receiptId: row.id } : { invoiceId: row.id }),
        amount: { amount: amount.trim(), currency },
        paidOn,
        method,
        reason: reason.trim(),
      },
      { onSuccess: () => onConfirmed(), onError: (err) => setError(err.message) },
    )
  }

  return (
    <div className="flow-sheet">
      <button type="button" className="scrim" aria-label={t('common:actions.close', { defaultValue: 'Close' })} onClick={onClose} />
      <section className="sheet" role="dialog" aria-modal="true" aria-labelledby="payment-sheet-h">
        <div className="sheet-head">
          <div>
            <h2 id="payment-sheet-h">{t('months:all.pay.title')}</h2>
            <p className="muted small">{rowTitle(t, row)}</p>
          </div>
          <button type="button" className="icon-button" aria-label={t('common:actions.close', { defaultValue: 'Close' })} onClick={onClose}>
            <Icon name="x" />
          </button>
        </div>
        <form className="sheet-body stack gap-4" onSubmit={submit}>
          <label className="field">
            <span className="label">{t('months:all.pay.amount', { currency })}</span>
            <input className="input" type="number" min="0.01" step="0.01" value={amount} onChange={(e) => setAmount(e.target.value)} required />
          </label>
          <label className="field">
            <span className="label">{t('months:all.pay.date')}</span>
            <input className="input" type="date" value={paidOn} onChange={(e) => setPaidOn(e.target.value)} required />
          </label>
          <label className="field">
            <span className="label">{t('months:all.pay.method')}</span>
            <select className="input" value={method} onChange={(e) => setMethod(e.target.value as Method)}>
              {METHODS.map((m) => (
                <option key={m} value={m}>
                  {t(`months:all.pay.methods.${m}`)}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span className="label">{t('months:all.pay.reason')}</span>
            <textarea className="input" rows={2} value={reason} onChange={(e) => setReason(e.target.value)} required />
          </label>
          <p className="muted">{t('months:all.pay.explain')}</p>
          {error && (
            <p className="muted" role="alert">
              {error}
            </p>
          )}
          <div className="row gap-3 justify-end">
            <Button type="button" variant="secondary" disabled={create.isPending} onClick={onClose}>
              {t('months:monthDetail.cancel', { defaultValue: 'Cancel' })}
            </Button>
            <Button type="submit" disabled={!ready}>
              {t('months:all.pay.confirm')}
            </Button>
          </div>
        </form>
      </section>
    </div>
  )
}
