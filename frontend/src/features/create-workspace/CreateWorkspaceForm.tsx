/**
 * The onboarding form of design/mocks/onboarding.html, with the mock's markup and kit classes
 * (ADR-019): who-choice, form-grid, disclosure for the optional bank account, trial note.
 */

import { zodResolver } from '@hookform/resolvers/zod'
import { useEffect, useMemo, useState, type KeyboardEvent } from 'react'
import { useForm, useWatch } from 'react-hook-form'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { trialPlan, usePlans } from '../../entities/plan'
import { CURRENCIES, currencyLabel, suggestCurrency } from '../../entities/workspace'
import { useAuth } from '../../entities/session'
import { ProblemError } from '../../shared/api/client'
import { Field, Input, Select } from '../../shared/ui/Field'
import { fieldErrorProps } from '../../shared/ui/fieldProps'
import { Icon, type IconName } from '../../shared/ui/Icon'
import onboardingEn from '../../shared/i18n/locales/en/onboarding.json'
import {
  createWorkspaceSchema,
  formFieldOf,
  toRequest,
  type CreateWorkspaceValues,
  type EntityType,
} from './schema'
import { timeZoneOptions } from './timeZones'
import { useCreateWorkspace } from './useCreateWorkspace'

const CHOICES: { value: EntityType; icon: IconName; label: string; hint: string }[] = [
  { value: 'INDIVIDUAL', icon: 'user', label: 'individual', hint: 'individualHint' },
  { value: 'COMPANY', icon: 'building', label: 'company', hint: 'companyHint' },
]

const INDUSTRY_KEYS = Object.keys(onboardingEn.industries)
type FieldName = Exclude<keyof CreateWorkspaceValues, 'entityType' | 'withBankAccount'>

export function CreateWorkspaceForm({ retryDelayMs }: { retryDelayMs?: number }) {
  const { t } = useTranslation('onboarding')
  const { t: tError } = useTranslation('errors')
  const navigate = useNavigate()
  const { user, signOut } = useAuth()
  const plans = usePlans()
  const trial = trialPlan(plans.data)
  const create = useCreateWorkspace(retryDelayMs)
  const [serverError, setServerError] = useState<string | null>(null)
  const { options: zones, current } = useMemo(() => timeZoneOptions(), [])

  const form = useForm<CreateWorkspaceValues>({
    resolver: zodResolver(createWorkspaceSchema),
    defaultValues: {
      entityType: 'COMPANY',
      name: '',
      tradingName: '',
      industry: '',
      timezone: current,
      currency: suggestCurrency(current),
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

  // The currency follows the time zone until the person picks one themselves (ADR-020).
  const timezone = useWatch({ control, name: 'timezone' })
  useEffect(() => {
    if (!form.getFieldState('currency').isDirty) setValue('currency', suggestCurrency(timezone))
  }, [timezone, form, setValue])

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

  const errorOf = (name: keyof CreateWorkspaceValues) => {
    const message = formState.errors[name]?.message
    return message ? t(message, { defaultValue: message }) : undefined
  }
  // id, aria and react-hook-form bindings per field, built outside the JSX.
  const field = (name: FieldName) => ({
    id: name,
    ...fieldErrorProps(name, errorOf(name)),
    ...register(name),
  })
  const bind = {
    name: field('name'),
    tradingName: field('tradingName'),
    industry: field('industry'),
    timezone: field('timezone'),
    currency: field('currency'),
    bankName: field('bankName'),
    holderName: field('holderName'),
    accountNumber: field('accountNumber'),
  }

  // Arrow keys move between the two choices, as in a native radio group.
  const onChoiceKey = (event: KeyboardEvent<HTMLButtonElement>) => {
    if (!['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(event.key)) return
    event.preventDefault()
    setValue('entityType', entityType === 'COMPANY' ? 'INDIVIDUAL' : 'COMPANY')
  }

  const busy = create.isPending
  const optional = <span className="muted">({t('optional')})</span>

  return (
    <form className="stack gap-6" onSubmit={onSubmit} noValidate>
      <div className="who-choice" role="radiogroup" aria-label={t('typeLabel')}>
        {CHOICES.map((choice) => {
          const checked = entityType === choice.value
          return (
            <button
              key={choice.value}
              type="button"
              role="radio"
              aria-checked={checked}
              tabIndex={checked ? 0 : -1}
              className={`who text-left${checked ? ' is-checked' : ''}`}
              onClick={() => setValue('entityType', choice.value)}
              onKeyDown={onChoiceKey}
            >
              {checked && (
                <span className="tick">
                  <Icon name="check" />
                </span>
              )}
              <span className="ico">
                <Icon name={choice.icon} />
              </span>
              <strong>{t(choice.label)}</strong>
              <span className="d">{t(choice.hint)}</span>
            </button>
          )
        })}
      </div>

      <div className="form-wrap">
        <div className="form-grid">
          <Field
            id="name"
            className="span-2"
            label={entityType === 'COMPANY' ? t('legalName') : t('fullName')}
            error={errorOf('name')}
          >
            <Input type="text" autoComplete="organization" {...bind.name} />
          </Field>
          <Field id="tradingName" label={<>{t('tradingName')} {optional}</>} error={errorOf('tradingName')}>
            <Input
              type="text"
              placeholder={t('tradingNamePlaceholder')}
              {...bind.tradingName}
            />
          </Field>
          <Field id="industry" label={t('industry')} error={errorOf('industry')}>
            <Select {...bind.industry}>
              <option value="">{t('industryChoose')}</option>
              {INDUSTRY_KEYS.map((key) => (
                <option key={key} value={t(`industries.${key}`)}>
                  {t(`industries.${key}`)}
                </option>
              ))}
            </Select>
          </Field>
          <Field
            id="timezone"
            label={t('timeZone')}
            hint={t('timeZoneHint')}
            error={errorOf('timezone')}
          >
            <Select {...bind.timezone}>
              {zones.map((option) => (
                <option key={option.zone} value={option.zone}>
                  {t('timeZoneOption', { zone: option.zone, offset: option.offset })}
                </option>
              ))}
            </Select>
          </Field>
          <Field id="currency" label={t('currency')} hint={t('currencyHint')} error={errorOf('currency')}>
            <Select {...bind.currency}>
              {CURRENCIES.map((code) => (
                <option key={code} value={code}>
                  {currencyLabel(code)}
                </option>
              ))}
            </Select>
          </Field>
        </div>
      </div>

      <details
        className="disclosure"
        open={withBankAccount}
        onToggle={(event) => setValue('withBankAccount', event.currentTarget.open)}
      >
        <summary>
          <span>
            {t('bankAccount')}
            <span className="opt">{t('optional')}</span>
          </span>
          <Icon name={withBankAccount ? 'chevron-up' : 'chevron-down'} />
        </summary>
        <div className="form-wrap pb-4">
          <div className="form-grid">
            <Field id="bankName" label={t('bankName')} error={errorOf('bankName')}>
              <Input type="text" {...bind.bankName} />
            </Field>
            <Field id="holderName" label={t('holderName')} error={errorOf('holderName')}>
              <Input type="text" {...bind.holderName} />
            </Field>
            <Field
              id="accountNumber"
              className="span-2"
              label={t('accountNumber')}
              hint={t('accountNumberHint')}
              error={errorOf('accountNumber')}
            >
              <Input
                type="text"
                inputMode="numeric"
                autoComplete="off"
                {...bind.accountNumber}
              />
            </Field>
          </div>
        </div>
      </details>

      {trial?.limits && (
        <p className="trial-note">
          <Icon name="clock" />
          <span>
            <strong>{t('trialLead', { days: trial.trialDays })}</strong>{' '}
            {t('trialRest', {
              documents: trial.limits.documentsPerMonth,
              pages: trial.limits.extractedPagesPerMonth,
            })}
          </span>
        </p>
      )}

      {serverError && (
        <p role="alert" className="trial-note bg-critical-soft text-critical">
          <Icon name="circle-alert" />
          <span>{serverError}</span>
        </p>
      )}
      {create.phase === 'finishing' && (
        <p role="status" className="muted">
          {t('finishing')}
        </p>
      )}
      {create.phase === 'notReady' && (
        <p role="alert" className="trial-note">
          <Icon name="info" />
          <span>{t('notReady')}</span>
        </p>
      )}

      <button type="submit" className="button button-primary button-lg button-block" disabled={busy}>
        {busy ? t('creating') : t('submit')}
      </button>

      <p className="small muted">
        {t('auth.signedInAsLine', { ns: 'common', email: user?.email ?? '' })}{' '}
        <button type="button" className="link border-0 bg-transparent p-0" onClick={() => void signOut()}>
          {t('auth.signOutShort', { ns: 'common' })}
        </button>
      </p>
    </form>
  )
}
