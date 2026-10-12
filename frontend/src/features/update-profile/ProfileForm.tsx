/**
 * Settings → Profile (docs/11 §6.9, AC-013-14): names, legal form, industry, tax ID (masked),
 * address, other names and time zone; the entity type is shown and fixed. AI suggestions for the
 * profile arrive with spec 014.
 */

import { useEffect, useMemo, useState } from 'react'
import { useForm } from 'react-hook-form'
import { useTranslation } from 'react-i18next'
import { currencyLabel, useUpdateWorkspace, type Workspace } from '../../entities/workspace'
import { ProblemError } from '../../shared/api/client'
import type { components } from '../../shared/api/schema'
import onboardingEn from '../../shared/i18n/locales/en/onboarding.json'
import { Badge } from '../../shared/ui/Badge'
import { Field, Input, Select } from '../../shared/ui/Field'
import { fieldErrorProps } from '../../shared/ui/fieldProps'
import { timeZoneOptions } from '../create-workspace/timeZones'

type LegalForm = components['schemas']['LegalForm']
const LEGAL_FORMS: LegalForm[] = ['LIMITED_COMPANY', 'PARTNERSHIP', 'SOLE_PROPRIETOR', 'COOPERATIVE', 'OTHER']
const INDUSTRY_KEYS = Object.keys(onboardingEn.industries)

interface Values {
  name: string
  tradingName: string
  legalForm: string
  industry: string
  taxId: string
  line1: string
  city: string
  aliases: string
  timezone: string
}

function valuesOf(ws: Workspace): Values {
  const p = ws.profile ?? {}
  return {
    name: ws.name,
    tradingName: p.tradingName ?? '',
    legalForm: p.legalForm ?? '',
    industry: p.industry ?? '',
    taxId: '',
    line1: p.address?.line1 ?? '',
    city: p.address?.city ?? '',
    aliases: (p.aliases ?? []).join('\n'),
    timezone: ws.timezone,
  }
}

export function ProfileForm({ workspace }: { workspace: Workspace }) {
  const { t } = useTranslation('settings')
  const update = useUpdateWorkspace()
  const [saved, setSaved] = useState(false)
  const [failure, setFailure] = useState<string | null>(null)
  const { options: zones } = useMemo(() => timeZoneOptions(), [])
  const form = useForm<Values>({ defaultValues: valuesOf(workspace) })
  const { register, formState, reset, setError } = form
  const company = workspace.entityType === 'COMPANY'
  const typeLabel = t(`entityTypes.${workspace.entityType}`, { ns: 'settings' })
  const industries = INDUSTRY_KEYS.map((key) => t(`industries.${key}`, { ns: 'onboarding' }))
  const currentIndustry = workspace.profile?.industry ?? ''
  const industryOptions = [...new Set([...industries, currentIndustry].filter(Boolean))]
  const masked = workspace.profile?.taxIdMasked

  // A saved PATCH returns the workspace; the form starts again from what the server stored.
  useEffect(() => reset(valuesOf(workspace)), [workspace, reset])

  const onSubmit = form.handleSubmit(async (values) => {
    setSaved(false)
    setFailure(null)
    const aliases = values.aliases.split('\n').map((line) => line.trim()).filter(Boolean)
    try {
      await update.mutateAsync({
        name: values.name.trim(),
        timezone: values.timezone,
        ...(values.taxId.trim() ? { taxId: values.taxId.trim() } : {}),
        profile: {
          legalName: values.name.trim(),
          tradingName: values.tradingName.trim() || undefined,
          industry: values.industry || undefined,
          ...(company && values.legalForm ? { legalForm: values.legalForm as LegalForm } : {}),
          address: { line1: values.line1.trim() || undefined, city: values.city.trim() || undefined },
          aliases,
        },
      })
      setSaved(true)
    } catch (error) {
      if (error instanceof ProblemError && error.code === 'VALIDATION_ERROR') {
        const errors = (error.problem.errors ?? []) as { field: string; message: string }[]
        for (const item of errors) {
          const key = item.field.split('.').pop() as keyof Values
          if (key in valuesOf(workspace)) setError(key, { message: item.message })
        }
      }
      const code = error instanceof ProblemError ? error.code : 'fallback'
      setFailure(t(code, { ns: 'errors', defaultValue: t('fallback', { ns: 'errors' }) }))
    }
  })

  const errorOf = (key: keyof Values) => formState.errors[key]?.message
  const field = (key: keyof Values) => ({ id: key, ...fieldErrorProps(key, errorOf(key)), ...register(key) })
  const bind = {
    name: field('name'),
    tradingName: field('tradingName'),
    legalForm: field('legalForm'),
    industry: field('industry'),
    taxId: field('taxId'),
    line1: field('line1'),
    city: field('city'),
    timezone: field('timezone'),
    aliases: field('aliases'),
  }
  const optional = <span className="muted">({t('profile.optional')})</span>

  return (
    <form className="panel panel-pad stack gap-6" onSubmit={onSubmit} noValidate>
      <p className="muted">{t('profile.intro')}</p>
      <div className="form-wrap">
        <div className="form-grid">
          <div className="field">
            <span className="label">{t('profile.type')}</span>
            <span>{typeLabel}</span>
            <span className="hint">{t('profile.typeFixed')}</span>
          </div>
          <div className="field">
            <span className="label">{t('language.currency')}</span>
            <span className="row gap-2 font-medium">
              {currencyLabel(workspace.currency)}
              <Badge variant="outline">{t('plan.comingSoon')}</Badge>
            </span>
            <span className="hint">{t('language.currencyFixed')}</span>
          </div>
          <Field
            id="name"
            className="span-2"
            label={company ? t('profile.legalName') : t('profile.fullName')}
            error={errorOf('name')}
          >
            <Input type="text" {...bind.name} />
          </Field>
          <Field id="tradingName" label={<>{t('profile.tradingName')} {optional}</>}>
            <Input type="text" {...bind.tradingName} />
          </Field>
          {company ? (
            <Field id="legalForm" label={<>{t('profile.legalForm')} {optional}</>}>
              <Select {...bind.legalForm}>
                <option value="">{t('profile.chooseLegalForm')}</option>
                {LEGAL_FORMS.map((legalForm) => (
                  <option key={legalForm} value={legalForm}>
                    {t(`profile.legalForms.${legalForm}`)}
                  </option>
                ))}
              </Select>
            </Field>
          ) : (
            <span aria-hidden="true" />
          )}
          <Field id="industry" label={<>{t('profile.industry')} {optional}</>}>
            <Select {...bind.industry}>
              <option value="">{t('industryChoose', { ns: 'onboarding' })}</option>
              {industryOptions.map((label) => (
                <option key={label} value={label}>
                  {label}
                </option>
              ))}
            </Select>
          </Field>
          <Field
            id="taxId"
            label={<>{t('profile.taxId')} {optional}</>}
            hint={masked ? t('profile.taxIdStored', { masked }) : t('profile.taxIdHint')}
            error={errorOf('taxId')}
          >
            <Input type="text" autoComplete="off" {...bind.taxId} />
          </Field>
          <Field id="line1" className="span-2" label={<>{t('profile.addressLine')} {optional}</>}>
            <Input type="text" {...bind.line1} />
          </Field>
          <Field id="city" label={<>{t('profile.city')} {optional}</>}>
            <Input type="text" {...bind.city} />
          </Field>
          <Field id="timezone" label={t('profile.timeZone')} error={errorOf('timezone')}>
            <Select {...bind.timezone}>
              {zones.map((option) => (
                <option key={option.zone} value={option.zone}>
                  {t('timeZoneOption', { ns: 'onboarding', zone: option.zone, offset: option.offset })}
                </option>
              ))}
            </Select>
          </Field>
          <Field
            id="aliases"
            className="span-2"
            label={<>{t('profile.aliases')} {optional}</>}
            hint={t('profile.aliasesHint')}
          >
            <textarea className="textarea" {...bind.aliases} />
          </Field>
        </div>
      </div>
      {failure && (
        <p role="alert" className="trial-note bg-critical-soft text-critical">
          {failure}
        </p>
      )}
      <div className="row">
        <button type="submit" className="button button-primary" disabled={update.isPending}>
          {update.isPending ? t('profile.saving') : t('profile.save')}
        </button>
        {saved && (
          <span role="status" className="muted small">
            {t('profile.saved')}
          </span>
        )}
      </div>
    </form>
  )
}
