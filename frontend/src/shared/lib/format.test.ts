import { describe, expect, it } from 'vitest'
import { formatDate } from './formatDate'
import { formatMoney } from './formatMoney'

describe('formatMoney', () => {
  it('formats standard amount with currency prefix', () => {
    const formatted = formatMoney(1250000, { currency: 'IDR' })
    expect(formatted).toContain('1,250,000')
  })

  it('formats compact amounts', () => {
    const formatted = formatMoney(1250000, { currency: 'IDR', compact: true })
    expect(formatted).toMatch(/1\.25.*M/)
  })

  it('handles string amounts', () => {
    const formatted = formatMoney('500000', { currency: 'IDR' })
    expect(formatted).toContain('500,000')
  })
})

describe('formatDate', () => {
  it('formats ISO date strings', () => {
    const formatted = formatDate('2026-10-11')
    expect(formatted).toContain('Oct')
    expect(formatted).toContain('2026')
  })

  it('handles invalid dates gracefully', () => {
    expect(formatDate('')).toBe('')
    expect(formatDate('invalid-date')).toBe('')
  })
})
