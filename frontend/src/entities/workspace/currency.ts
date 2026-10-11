/** The workspace's currency (ADR-020): chosen at onboarding, fixed afterwards. */

import type { components } from '../../shared/api/schema'
import { activeLocale } from '../../shared/lib/activeLocale'

export type Currency = components['schemas']['Currency']

export const CURRENCIES = ['IDR', 'MYR', 'SGD', 'JPY', 'USD'] as const satisfies readonly Currency[]

// Every member of the contract's enum must be offered; this line fails to compile if one is missing.
const _complete: Record<Currency, true> = { IDR: true, MYR: true, SGD: true, JPY: true, USD: true }
void _complete

const BY_ZONE: Record<string, Currency> = {
  'Asia/Jakarta': 'IDR',
  'Asia/Pontianak': 'IDR',
  'Asia/Makassar': 'IDR',
  'Asia/Jayapura': 'IDR',
  'Asia/Kuala_Lumpur': 'MYR',
  'Asia/Kuching': 'MYR',
  'Asia/Singapore': 'SGD',
  'Asia/Tokyo': 'JPY',
}

/** A starting point from the browser's time zone; the person confirms or changes it. */
export function suggestCurrency(timeZone: string): Currency {
  return BY_ZONE[timeZone] ?? 'USD'
}

/** "Malaysian Ringgit (MYR)", named by Intl in the active language. */
export function currencyLabel(code: Currency): string {
  const name = new Intl.DisplayNames([activeLocale()], { type: 'currency' }).of(code) ?? code
  return `${name} (${code})`
}
