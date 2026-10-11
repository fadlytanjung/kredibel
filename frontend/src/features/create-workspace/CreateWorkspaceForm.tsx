import { zodResolver } from '@hookform/resolvers/zod'
import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { useForm, useWatch } from 'react-hook-form'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { trialPlan, usePlans } from '../../entities/plan'
import { useAuth } from '../../entities/session'
import { ProblemError } from '../../shared/api/client'
import { Button } from '../../shared/ui/Button'
import {
  createWorkspaceSchema,
  formFieldOf,
  toRequest,
  type CreateWorkspaceValues,
  type EntityType,
} from './schema'
import { useCreateWorkspace } from './useCreateWorkspace'

const INPUT_CLASS =
  'w-full h-10 px-3 rounded-xs border border-line bg-surface text-ink text-sm focus:outline-none focus:border-brand focus:ring-1 focus:ring-brand aria-invalid:border-critical'

const CHOICES: { value: EntityType; label: string; hint: string }[] = [
  { value: 'INDIVIDUAL', label: 'individual', hint: 'individualHint' },
  { value: 'COMPANY', label: 'company', hint: 'companyHint' },
]

function browserTimeZones(): { zones: string[]; current: string } {
  const current = Intl.DateTimeFormat().resolvedOptions().timeZone || 'Asia/Jakarta'
  const zones = Intl.supportedValuesOf('timeZone')
  return { zones: zones.includes(current) ? zones : [current, ...zones], current }
}

function Field({
  id,
  label,
  error,
  hint,
  children,
}: {
  id: string
  label: ReactNode
  error?: string
  hint?: string
  children: ReactNode
}) {
  return (
    <div>
      <label htmlFor={id} className="block text-xs font-semibold text-ink mb-1">
        {label}
      </label>
      {children}
      {error ? (
        <p id={`${id}-error`} className="mt-1 text-xs text-critical">
          {error}
        </p>
      ) : (
        hint && <p className="mt-1 text-xs text-ink-muted">{hint}</p>
      )}
    </div>
  )
}

export function CreateWorkspaceForm({ retryDelayMs }: { retryDelayMs?: number }) {
  const { t } = useTranslation('onboarding')
  const { t: tError } = useTranslation('errors')
  const navigate = useNavigate()
  const { user, signOut } = useAuth()
  const plans = usePlans()
  const trial = trialPlan(plans.data)
  const create = useCreateWorkspace(retryDelayMs)
  const [serverError, setServerError] = useState<string | null>(null)
  const { zones, current } = useMemo(() => browserTimeZones(), [])

  const form = useForm<CreateWorkspaceValues>({
    resolver: zodResolver(createWorkspaceSchema),
    defaultValues: {
      entityType: 'COMPANY',
      name: '',
      tradingName: '',
      industry: '',
      timezone: current,
      withBankAccount: false,
      bankName: '',
      accountNumber: '',
      holderName: '',
    },
  })
  const { register, setValue, formState, control } = form
  const entityType = useWatch({ control, name: 'entityType' })
  const withBankAccount = useWatch({ control, name: 'withBankAccount' })

  useEffect(() => {
    if (create.phase === 'done') navigate('/', { replace: true })
  }, [create.phase, navigate])

  const onSubmit = form.handleSubmit(async (values) => {
    setServerError(null)
    try {
      await create.mutateAsync(toRequest(values))
    } catch (error) {
      if (error instanceof ProblemError && error.code === 'VALIDATION_ERROR') {
        const errors = (error.problem.errors ?? []) as { field: string; message: string }[]
        for (const item of errors) {
          const field = formFieldOf(item.field)
          if (field) form.setError(field, { message: item.message })
        }
      }
      const code = error instanceof ProblemError ? error.code : 'fallback'
      setServerError(tError(code, { defaultValue: tError('fallback') }))
    }
  })

  const fieldError = (name: keyof CreateWorkspaceValues) => {
    const message = formState.errors[name]?.message
    return message ? t(message, { defaultValue: message }) : undefined
  }
  const invalid = (name: keyof CreateWorkspaceValues) => ({
    'aria-invalid': Boolean(formState.errors[name]),
    'aria-describedby': formState.errors[name] ? `${name}-error` : undefined,
  })
  const busy = create.isPending
  const optional = <span className="text-ink-subtle font-normal">{t('optional')}</span>

  return (
    <form className="space-y-6" onSubmit={onSubmit} noValidate>
      <div className="grid grid-cols-2 gap-3" role="radiogroup" aria-label={t('typeLabel')}>
        {CHOICES.map((choice) => {
          const selected = entityType === choice.value
          return (
            <button
              key={choice.value}
              type="button"
              role="radio"
              aria-checked={selected}
              onClick={() => setValue('entityType', choice.value)}
              className={`flex flex-col justify-start p-4 rounded-xs border text-left transition-colors cursor-pointer ${
                selected
                  ? 'border-brand bg-brand-soft ring-1 ring-brand'
                  : 'border-line bg-surface hover:bg-sunken'
              }`}
            >
              <div className="font-semibold text-sm text-ink mb-1">{t(choice.label)}</div>
              <div className="text-xs text-ink-muted leading-relaxed">{t(choice.hint)}</div>
            </button>
          )
        })}
      </div>

      <div className="space-y-4">
        <Field
          id="name"
          label={entityType === 'COMPANY' ? t('legalName') : t('fullName')}
          error={fieldError('name')}
        >
          <input id="name" type="text" className={INPUT_CLASS} {...invalid('name')} {...register('name')} />
        </Field>

        <Field id="tradingName" label={<>{t('tradingName')} {optional}</>} error={fieldError('tradingName')}>
          <input
            id="tradingName"
            type="text"
            placeholder={t('tradingNamePlaceholder')}
            className={INPUT_CLASS}
            {...invalid('tradingName')}
            {...register('tradingName')}
          />
        </Field>

        <div className="grid grid-cols-1 medium:grid-cols-2 gap-4">
          <Field id="industry" label={<>{t('industry')} {optional}</>} error={fieldError('industry')}>
            <input
              id="industry"
              type="text"
              placeholder={t('industryPlaceholder')}
              className={INPUT_CLASS}
              {...invalid('industry')}
              {...register('industry')}
            />
          </Field>
          <Field id="timezone" label={t('timeZone')} hint={t('timeZoneHint')} error={fieldError('timezone')}>
            <select id="timezone" className={INPUT_CLASS} {...invalid('timezone')} {...register('timezone')}>
              {zones.map((zone) => (
                <option key={zone} value={zone}>
                  {zone}
                </option>
              ))}
            </select>
          </Field>
        </div>

        {withBankAccount ? (
          <fieldset className="space-y-4 rounded-xs border border-line p-4">
            <legend className="px-1 text-xs font-semibold text-ink">{t('bankAccount')}</legend>
            <Field id="bankName" label={t('bankName')} error={fieldError('bankName')}>
              <input id="bankName" type="text" className={INPUT_CLASS} {...invalid('bankName')} {...register('bankName')} />
            </Field>
            <Field
              id="accountNumber"
              label={t('accountNumber')}
              hint={t('accountNumberHint')}
              error={fieldError('accountNumber')}
            >
              <input
                id="accountNumber"
                type="text"
                inputMode="numeric"
                autoComplete="off"
                className={INPUT_CLASS}
                {...invalid('accountNumber')}
                {...register('accountNumber')}
              />
            </Field>
            <Field id="holderName" label={t('holderName')} error={fieldError('holderName')}>
              <input
                id="holderName"
                type="text"
                className={INPUT_CLASS}
                {...invalid('holderName')}
                {...register('holderName')}
              />
            </Field>
            <button
              type="button"
              onClick={() => setValue('withBankAccount', false)}
              className="text-xs font-semibold text-ink-muted hover:text-ink cursor-pointer"
            >
              {t('removeBankAccount')}
            </button>
          </fieldset>
        ) : (
          <button
            type="button"
            onClick={() => setValue('withBankAccount', true)}
            className="text-sm font-semibold text-brand hover:underline cursor-pointer"
          >
            {t('addBankAccount')}
          </button>
        )}
      </div>

      {trial?.limits && (
        <p className="p-3 rounded-xs bg-sunken text-xs text-ink-muted">
          {t('trialTerms', {
            days: trial.trialDays,
            documents: trial.limits.documentsPerMonth,
            pages: trial.limits.extractedPagesPerMonth,
          })}
        </p>
      )}

      {serverError && (
        <div role="alert" className="rounded-xs bg-critical-soft p-3 text-xs font-medium text-critical">
          {serverError}
        </div>
      )}
      {create.phase === 'finishing' && <p role="status" className="text-sm text-ink-muted">{t('finishing')}</p>}
      {create.phase === 'notReady' && (
        <div role="alert" className="rounded-xs bg-sunken p-3 text-xs text-ink">
          {t('notReady')}
        </div>
      )}

      <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
        <button type="button" onClick={() => void signOut()} className="text-xs text-ink-muted hover:text-ink cursor-pointer">
          {t('auth.signOutAs', { ns: 'common', email: user?.email ?? '' })}
        </button>
        <Button type="submit" variant="primary" size="lg" disabled={busy}>
          {busy ? t('creating') : t('submit')}
        </Button>
      </div>
    </form>
  )
}
