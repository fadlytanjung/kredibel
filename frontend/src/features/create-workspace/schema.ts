/**
 * Onboarding form values and their mapping to POST /api/workspaces (contracts/openapi.yaml
 * WorkspaceCreate). Messages are i18n keys in the onboarding namespace.
 */

import { z } from 'zod'
import { CURRENCIES } from '../../entities/workspace'
import type { components } from '../../shared/api/schema'

export type WorkspaceCreate = components['schemas']['WorkspaceCreate']

// Kredibel is for businesses (AC-013-2): every workspace is a company.
export const LEGAL_FORMS = ['LIMITED_COMPANY', 'PARTNERSHIP', 'SOLE_PROPRIETOR', 'COOPERATIVE', 'OTHER'] as const
export const FRAMEWORKS = ['IFRS', 'US_GAAP'] as const

const optionalText = (max: number) =>
  z.string().trim().max(max, 'validation.tooLong').optional().or(z.literal(''))

export const createWorkspaceSchema = z
  .object({
    name: z.string().trim().min(2, 'validation.nameLength').max(100, 'validation.nameLength'),
    tradingName: optionalText(200),
    legalForm: z.enum(LEGAL_FORMS),
    industry: optionalText(100),
    taxId: optionalText(30),
    framework: z.enum(FRAMEWORKS),
    timezone: z.string().min(1, 'validation.required'),
    currency: z.enum(CURRENCIES),
    withBankAccount: z.boolean(),
    bankName: optionalText(100),
    accountNumber: optionalText(30),
    holderName: optionalText(200),
  })
  .superRefine((values, ctx) => {
    if (!values.withBankAccount) return
    for (const field of ['bankName'] as const) {
      if (!values[field]) ctx.addIssue({ code: 'custom', path: [field], message: 'validation.required' })
    }
    // Same pattern as BankAccountCreate.accountNumber in the contract.
    if (!/^[0-9 -]{6,30}$/.test(values.accountNumber ?? '')) {
      ctx.addIssue({ code: 'custom', path: ['accountNumber'], message: 'validation.accountNumber' })
    }
  })

export type CreateWorkspaceValues = z.infer<typeof createWorkspaceSchema>

export function toRequest(values: CreateWorkspaceValues): WorkspaceCreate {
  const profile: NonNullable<WorkspaceCreate['profile']> = {
    legalName: values.name,
    legalForm: values.legalForm,
    accountingFramework: values.framework,
  }
  if (values.tradingName) profile.tradingName = values.tradingName
  if (values.industry) profile.industry = values.industry
  return {
    name: values.name,
    entityType: 'COMPANY',
    country: 'ID',
    timezone: values.timezone,
    currency: values.currency,
    profile,
    ...(values.taxId ? { taxId: values.taxId } : {}),
    ...(values.withBankAccount
      ? {
          bankAccounts: [
            {
              bankName: values.bankName ?? '',
              accountNumber: values.accountNumber ?? '',
              holderName: values.holderName || values.name,
            },
          ],
        }
      : {}),
  }
}

/** "body.bankAccounts.0.accountNumber" → "accountNumber": server field errors onto form fields. */
export function formFieldOf(serverField: string): keyof CreateWorkspaceValues | undefined {
  const last = serverField.split('.').pop() ?? ''
  const known: (keyof CreateWorkspaceValues)[] = [
    'name',
    'tradingName',
    'legalForm',
    'industry',
    'taxId',
    'timezone',
    'currency',
    'bankName',
    'accountNumber',
    'holderName',
  ]
  return known.find((field) => field === last)
}
