/**
 * The onboarding form of design/mocks/onboarding.html, with the mock's markup and kit classes
 * (ADR-019). Kredibel is for businesses (AC-013-2): three sections, Your business, Your books
 * (currency, a segmented accounting framework, time zone) and an optional main bank account.
 */

import { zodResolver } from '@hookform/resolvers/zod'
import { useEffect, useMemo, useRef, useState, type ChangeEvent } from 'react'
import { useForm, useWatch } from 'react-hook-form'
import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { trialPlan, usePlans } from '../../entities/plan'
import { CURRENCIES, currencyLabel, suggestCurrency } from '../../entities/workspace'
import { useAuth } from '../../entities/session'
import { ProblemError } from '../../shared/api/client'
import { Field, Input, Select } from '../../shared/ui/Field'
import { fieldErrorProps } from '../../shared/ui/fieldProps'
import { Icon } from '../../shared/ui/Icon'
import onboardingEn from '../../shared/i18n/locales/en/onboarding.json'
import {
  createWorkspaceSchema,
  formFieldOf,
  FRAMEWORKS,
  LEGAL_FORMS,
  toRequest,
  type CreateWorkspaceValues,
} from './schema'
import { timeZoneOptions } from './timeZones'
import { useCreateWorkspace } from './useCreateWorkspace'

const INDUSTRY_KEYS = Object.keys(onboardingEn.industries)
type FieldName = Exclude<keyof CreateWorkspaceValues, 'withBankAccount' | 'framework'>

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
      name: '',
      tradingName: '',
      legalForm: 'LIMITED_COMPANY',
      industry: '',
      taxId: '',
      framework: 'IFRS',
      timezone: current,
      currency: suggestCurrency(current),
      withBankAccount: false,
      bankName: '',
      accountNumber: '',
      holderName: '',
    },
  })
  const { register, setValue, formState, control } = form
  const framework = useWatch({ control, name: 'framework' })
  const withBankAccount = useWatch({ control, name: 'withBankAccount' })

  useEffect(() => {
    if (create.phase === 'done') navigate('/', { replace: true })
  }, [create.phase, navigate])

  // The currency follows the time zone until the person picks one themselves (ADR-020). A pick
  // is remembered as such: picking the suggested currency is still a choice, which isDirty misses.
  const currencyPicked = useRef(false)
  const timezone = useWatch({ control, name: 'timezone' })
  useEffect(() => {
    if (!currencyPicked.current) setValue('currency', suggestCurrency(timezone))
  }, [timezone, setValue])

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
    legalForm: field('legalForm'),
    industry: field('industry'),
    taxId: field('taxId'),
    timezone: field('timezone'),
    currency: field('currency'),
    bankName: field('bankName'),
    holderName: field('holderName'),
    accountNumber: field('accountNumber'),
  }

  const busy = create.isPending
  const optional = <span className="muted">({t('optional')})</span>

  return (
    <form className="stack gap-6" onSubmit={onSubmit} noValidate>
      <section className="form-section" aria-labelledby="ob-business">
        <h2 id="ob-business">{t('sectionBusiness')}</h2>
        <div className="form-wrap">
          <div className="form-grid">
            <Field id="name" className="span-2" label={t('legalName')} error={errorOf('name')}>
              <Input type="text" autoComplete="organization" {...bind.name} />
            </Field>
            <Field id="tradingName" label={<>{t('tradingName')} {optional}</>} error={errorOf('tradingName')}>
              <Input type="text" placeholder={t('tradingNamePlaceholder')} {...bind.tradingName} />
            </Field>
            <Field id="legalForm" label={t('legalForm')} error={errorOf('legalForm')}>
              <Select {...bind.legalForm}>
                {LEGAL_FORMS.map((form) => (
                  <option key={form} value={form}>
                    {t(`legalForms.${form}`)}
                  </option>
                ))}
              </Select>
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
            <Field id="taxId" label={<>{t('taxId')} {optional}</>} error={errorOf('taxId')}>
              <Input type="text" autoComplete="off" placeholder={t('taxIdPlaceholder')} {...bind.taxId} />
            </Field>
          </div>
        </div>
      </section>

      <section className="form-section" aria-labelledby="ob-books">
        <h2 id="ob-books">{t('sectionBooks')}</h2>
        <div className="form-wrap">
          <div className="form-grid">
            <Field id="currency" label={t('currency')} hint={t('currencyHint')} error={errorOf('currency')}>
              <Select
                {...bind.currency}
                onChange={(event: ChangeEvent<HTMLSelectElement>) => {
                  currencyPicked.current = true
                  void bind.currency.onChange(event)
                }}
              >
                {CURRENCIES.map((code) => (
                  <option key={code} value={code}>
                    {currencyLabel(code)}
                  </option>
                ))}
              </Select>
            </Field>
            <Field id="timezone" label={t('timeZone')} hint={t('timeZoneHint')} error={errorOf('timezone')}>
              <Select {...bind.timezone}>
                {zones.map((option) => (
                  <option key={option.zone} value={option.zone}>
                    {t('timeZoneOption', { zone: option.zone, offset: option.offset })}
                  </option>
                ))}
              </Select>
            </Field>
            <div className="field span-2">
              <span className="label" id="framework-label">
                {t('framework')}
              </span>
              <div className="seg" role="group" aria-labelledby="framework-label">
                {FRAMEWORKS.map((value) => (
                  <button
                    key={value}
                    type="button"
                    aria-pressed={framework === value}
                    onClick={() => setValue('framework', value)}
                  >
                    {t(`frameworks.${value}`)}
                  </button>
                ))}
              </div>
              <span className="hint">{t('frameworkHint')}</span>
            </div>
          </div>
        </div>
      </section>

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
