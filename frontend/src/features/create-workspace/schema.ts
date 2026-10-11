/**
 * Onboarding form values and their mapping to POST /api/workspaces (contracts/openapi.yaml
 * WorkspaceCreate). Messages are i18n keys in the onboarding namespace.
 */

import { z } from 'zod'
import { CURRENCIES } from '../../entities/workspace'
import type { components } from '../../shared/api/schema'

export type WorkspaceCreate = components['schemas']['WorkspaceCreate']
export type EntityType = components['schemas']['EntityType']

const optionalText = (max: number) =>
  z.string().trim().max(max, 'validation.tooLong').optional().or(z.literal(''))

export const createWorkspaceSchema = z
  .object({
    entityType: z.enum(['INDIVIDUAL', 'COMPANY']),
    name: z.string().trim().min(2, 'validation.nameLength').max(100, 'validation.nameLength'),
    tradingName: optionalText(200),
    industry: optionalText(100),
    timezone: z.string().min(1, 'validation.required'),
    currency: z.enum(CURRENCIES),
    withBankAccount: z.boolean(),
    bankName: optionalText(100),
    accountNumber: optionalText(30),
    holderName: optionalText(200),
  })
  .superRefine((values, ctx) => {
    if (!values.withBankAccount) return
    for (const field of ['bankName', 'holderName'] as const) {
      if (!values[field]) ctx.addIssue({ code: 'custom', path: [field], message: 'validation.required' })
    }
    // Same pattern as BankAccountCreate.accountNumber in the contract.
    if (!/^[0-9 -]{6,30}$/.test(values.accountNumber ?? '')) {
      ctx.addIssue({ code: 'custom', path: ['accountNumber'], message: 'validation.accountNumber' })
    }
  })

export type CreateWorkspaceValues = z.infer<typeof createWorkspaceSchema>

export function toRequest(values: CreateWorkspaceValues): WorkspaceCreate {
  const profile: WorkspaceCreate['profile'] = {}
  if (values.tradingName) profile.tradingName = values.tradingName
  if (values.industry) profile.industry = values.industry
  return {
    name: values.name,
    entityType: values.entityType,
    country: 'ID',
    timezone: values.timezone,
    currency: values.currency,
    ...(Object.keys(profile).length ? { profile } : {}),
    ...(values.withBankAccount
      ? {
          bankAccounts: [
            {
              bankName: values.bankName ?? '',
              accountNumber: values.accountNumber ?? '',
              holderName: values.holderName ?? '',
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
    'industry',
    'timezone',
    'currency',
    'bankName',
    'accountNumber',
    'holderName',
    'entityType',
  ]
  return known.find((field) => field === last)
}
