/**
 * design/mocks/welcome.html (spec 024, AC-024-4): asked once after onboarding, with no navigation:
 * keep the books, or write the money in and out expected per month first. Either way the dashboard
 * follows; the expectations are compared with the reconciled months there.
 */
import { useState, type FormEvent } from 'react'
import { useTranslation } from 'react-i18next'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useUpdateWorkspace, useWorkspace, type WorkspaceUpdate } from '../entities/workspace'
import { ExpectationRows, amountOf, type ExpectationRow } from '../features/expectations'
import { currentMonth } from '../shared/lib/formatDate'
import { Icon } from '../shared/ui'
import { AuthBrandPanel } from '../widgets/AuthBrandPanel'

function previousMonth(month: string): string {
  const [y, m] = month.split('-').map(Number)
  return m === 1 ? `${y - 1}-12` : `${y}-${String(m - 1).padStart(2, '0')}`
}

const whole = (amount?: string | null) => (amount ? amount.replace(/\.00$/, '') : '')

function ExpectForm({ initial, currency, pending, failed, onSave }: { initial: ExpectationRow[]; currency: string; pending: boolean; failed: boolean; onSave: (patch: WorkspaceUpdate) => void }) {
  const { t } = useTranslation(['onboarding', 'errors'])
  const [rows, setRows] = useState(initial)
  const [invalid, setInvalid] = useState(false)

  const save = (event: FormEvent) => {
    event.preventDefault()
    const expectations = rows.map((row) => ({ month: row.month, moneyIn: amountOf(row.moneyIn), moneyOut: amountOf(row.moneyOut) }))
    const bad = expectations.some((e) => !/^\d{4}-\d{2}$/.test(e.month) || e.moneyIn === undefined || e.moneyOut === undefined || (e.moneyIn === null && e.moneyOut === null))
    setInvalid(bad)
    if (!bad) onSave({ goal: 'CHECK_EXPECTATIONS', expectations })
  }

  return (
    <form className="form-section stack gap-4" aria-labelledby="welcome-form-h" onSubmit={save} noValidate>
      <h2 id="welcome-form-h">{t('welcome.form.title')}</h2>
      <ExpectationRows rows={rows} currency={currency} onChange={setRows} />
      <div className="actions">
        <button type="button" className="button button-secondary" disabled={rows.length >= 12} onClick={() => setRows([...rows, { month: '', moneyIn: '', moneyOut: '' }])}>
          <Icon name="plus" size="sm" />
          {t('welcome.form.add')}
        </button>
      </div>
      {invalid && (
        <p className="small status-line bad" role="alert">
          {t('welcome.form.invalid')}
        </p>
      )}
      {failed && (
        <p className="small status-line bad" role="alert">
          {t('errors:fallback')}
        </p>
      )}
      <button type="submit" className="button button-primary button-lg button-block" disabled={pending}>
        {t(pending ? 'welcome.form.saving' : 'welcome.form.save')}
      </button>
    </form>
  )
}

export function WelcomePage() {
  const { t } = useTranslation('onboarding')
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const workspace = useWorkspace(true)
  const update = useUpdateWorkspace()
  const [choice, setChoice] = useState<'expect' | null>(searchParams.get('expect') === '1' ? 'expect' : null)
  const saved = workspace.data?.expectations ?? []
  // Changing them later: the form starts from what was saved.
  const initial = saved.length
    ? saved.map((e) => ({ month: e.month, moneyIn: whole(e.moneyIn), moneyOut: whole(e.moneyOut) }))
    : [{ month: previousMonth(currentMonth()), moneyIn: '', moneyOut: '' }]
  const toDashboard = () => navigate('/dashboard', { replace: true })
  // Skipping keeps the books, the default, so the question is not asked again (Settings changes it).
  const skip = () => submit({ goal: 'BOOKKEEPING' })
  const submit = (patch: WorkspaceUpdate) => update.mutate(patch, { onSuccess: toDashboard })

  return (
    <div className="viewport">
      <div className="onboard">
        <AuthBrandPanel />
        <section className="onboard-form" aria-labelledby="welcome-h">
          <div className="stack gap-2">
            <h1 className="type-title" id="welcome-h">
              {t('welcome.title')}
            </h1>
            <p className="muted">{t('welcome.subtitle')}</p>
          </div>
          <div className="welcome-choices">
            <button type="button" className="welcome-choice" disabled={update.isPending} onClick={() => submit({ goal: 'BOOKKEEPING' })}>
              <Icon name="reconcile" />
              <span className="stack gap-1">
                <span className="w-t">{t('welcome.books.title')}</span>
                <span className="w-b">{t('welcome.books.body')}</span>
              </span>
            </button>
            <button type="button" className="welcome-choice" aria-expanded={choice === 'expect'} onClick={() => setChoice('expect')}>
              <Icon name="scale" />
              <span className="stack gap-1">
                <span className="w-t">{t('welcome.expect.title')}</span>
                <span className="w-b">{t('welcome.expect.body')}</span>
              </span>
            </button>
          </div>
          {choice === 'expect' && (
            <ExpectForm key={saved.length ? 'saved' : 'new'} initial={initial} currency={workspace.data?.currency ?? 'IDR'} pending={update.isPending} failed={update.isError} onSave={submit} />
          )}
          <button type="button" className="button button-quiet welcome-skip" disabled={update.isPending} onClick={skip}>
            {t('welcome.skip')}
          </button>
        </section>
      </div>
    </div>
  )
}
