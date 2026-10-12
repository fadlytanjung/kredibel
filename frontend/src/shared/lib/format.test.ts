import { afterEach, describe, expect, it } from 'vitest'
import i18n from '../i18n/setup'
import { formatDate, formatMonth } from './formatDate'
import { formatAmount, formatMoney } from './formatMoney'

const ORIGINAL_TZ = process.env.TZ

// A second UI language only becomes active once it has resources, as a real one would.
i18n.addResourceBundle('de', 'common', { app: { name: 'Kredibel' } })

afterEach(async () => {
  process.env.TZ = ORIGINAL_TZ
  await i18n.changeLanguage('en')
})

describe('formatMoney (AC-001-14)', () => {
  it('formats standard amount with currency prefix', () => {
    expect(formatMoney('1250000.00', { currency: 'IDR' })).toContain('1,250,000')
  })

  it('formats compact amounts', () => {
    // CLDR 48 writes the British million as "m" (IDR 1.25m); earlier data wrote "M".
    expect(formatMoney('1250000', { currency: 'IDR', compact: true })).toMatch(/1\.25\s*[mM]$/)
  })

  it('keeps every digit of a decimal string (money is never a float)', () => {
    // 2^53 + 1 cannot be represented as a float; parseFloat would print ...992.
    expect(formatMoney('9007199254740993', { currency: 'IDR' })).toContain('9,007,199,254,740,993')
  })

  it('keeps the sign of an outgoing amount', () => {
    expect(formatMoney('-32100000.00', { currency: 'IDR' })).toMatch(/-.*32,100,000/)
  })

  it('rejects a value that is not a decimal string', () => {
    expect(formatMoney('12abc', { currency: 'IDR' })).toBe('')
  })

  it.each([
    ['IDR', '1250000.00', 'IDR 1,250,000'],
    ['JPY', '3000.00', 'JPY 3,000'],
    ['MYR', '1250.50', 'MYR 1,250.50'],
    ['SGD', '980.05', 'SGD 980.05'],
    ['USD', '12.00', 'USD 12.00'],
  ])('shows %s in its own decimals (ADR-020)', (currency, amount, shown) => {
    expect(formatMoney(amount, { currency, code: true }).replace(/\s/g, ' ')).toBe(shown)
  })

  it('uses the active i18n locale', async () => {
    await i18n.changeLanguage('de')
    expect(formatMoney('1250000', { currency: 'IDR' })).toContain('1.250.000')
  })
})

describe('formatDate (AC-001-14)', () => {
  it('formats ISO date strings', () => {
    const formatted = formatDate('2026-10-11')
    expect(formatted).toContain('Oct')
    expect(formatted).toContain('2026')
  })

  it('shows a calendar date as that day in every time zone', () => {
    process.env.TZ = 'America/Los_Angeles'
    expect(formatDate('2026-10-11')).toContain('11')
  })

  it('handles invalid dates gracefully', () => {
    expect(formatDate('')).toBe('')
    expect(formatDate('invalid-date')).toBe('')
  })

  it('uses the active i18n locale', async () => {
    await i18n.changeLanguage('de')
    expect(formatDate('2026-10-11')).toContain('Okt')
  })
})

describe('formatAmount', () => {
  it('prints the amount once, without its currency, in the currency’s own digits', () => {
    expect(formatAmount('2502.33', { currency: 'MYR' })).toBe('2,502.33')
    expect(formatAmount('-5831.45', { currency: 'MYR' })).toBe('-5,831.45')
    expect(formatAmount('41100000.00', { currency: 'IDR' })).toBe('41,100,000')
    expect(formatAmount('12345678901234567.89', { currency: 'USD' })).toBe('12,345,678,901,234,567.89')
    expect(formatAmount('not money', { currency: 'MYR' })).toBe('')
  })
})

describe('formatMonth', () => {
  it('names a calendar month the same in every time zone', () => {
    expect(formatMonth('2026-03', 'short')).toBe('Mar')
    expect(formatMonth('2026-03', 'long')).toBe('March')
    expect(formatMonth('2026-03')).toBe('March 2026')
    expect(formatMonth('not a month')).toBe('not a month')
  })
})
