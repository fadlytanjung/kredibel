import { describe, expect, it } from 'vitest'
import { CURRENCIES, currencyLabel, suggestCurrency } from './currency'

describe('workspace currency (ADR-020)', () => {
  it('offers the five currencies of the contract', () => {
    expect(CURRENCIES).toEqual(['IDR', 'MYR', 'SGD', 'JPY', 'USD'])
  })

  it.each([
    ['Asia/Jakarta', 'IDR'],
    ['Asia/Makassar', 'IDR'],
    ['Asia/Jayapura', 'IDR'],
    ['Asia/Kuala_Lumpur', 'MYR'],
    ['Asia/Kuching', 'MYR'],
    ['Asia/Singapore', 'SGD'],
    ['Asia/Tokyo', 'JPY'],
    ['Europe/London', 'USD'],
  ])('suggests %s → %s', (zone, currency) => {
    expect(suggestCurrency(zone)).toBe(currency)
  })

  it('names a currency in words with its code', () => {
    expect(currencyLabel('MYR')).toBe('Malaysian Ringgit (MYR)')
  })
})
