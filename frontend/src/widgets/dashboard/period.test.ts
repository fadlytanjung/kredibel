import { describe, expect, it } from 'vitest'
import { clampRange, currentMonthIn, monthOptions, parsePeriod, periodKey, switchKind, yearOptions } from './period'

describe('the dashboard period (spec 010, AC-010-1)', () => {
  it('reads and writes a month, a range of at most 12 months and a year', () => {
    expect(parsePeriod('2026-10')).toEqual({ kind: 'month', from: '2026-10', to: '2026-10' })
    expect(parsePeriod('2026')).toEqual({ kind: 'year', from: '2026-01', to: '2026-12' })
    expect(parsePeriod('2025-11..2026-10')).toEqual({ kind: 'range', from: '2025-11', to: '2026-10' })
    expect(parsePeriod('2025-10..2026-10')).toBeNull()
    expect(parsePeriod('2026-03..2026-01')).toBeNull()
    expect(parsePeriod('recent')).toBeNull()
    expect(periodKey({ kind: 'range', from: '2026-08', to: '2026-10' })).toBe('2026-08..2026-10')
  })

  it('takes today in the workspace time zone', () => {
    const lateOnTheLastDay = new Date('2026-10-31T20:00:00Z')
    expect(currentMonthIn('Asia/Jakarta', lateOnTheLastDay)).toBe('2026-11')
    expect(currentMonthIn('UTC', lateOnTheLastDay)).toBe('2026-10')
    expect(currentMonthIn('Not/AZone', lateOnTheLastDay)).toMatch(/^2026-1[01]$/)
  })

  it('offers months from the earliest books or two years back to today, newest first', () => {
    const months = monthOptions(['2026-01', '2026-06'], '2026-10')
    expect(months[0]).toBe('2026-10')
    expect(months.at(-1)).toBe('2024-11')
    expect(monthOptions(['2023-05'], '2026-10').at(-1)).toBe('2023-05')
    expect(yearOptions(['2026-01'], '2026-10')).toEqual(['2026', '2025', '2024'])
  })

  it('keeps a range inside 12 months and not past today', () => {
    expect(clampRange('2025-01', '2026-10', '2026-10')).toEqual({ kind: 'range', from: '2025-01', to: '2025-12' })
    expect(clampRange('2026-09', '2026-12', '2026-10').to).toBe('2026-10')
    expect(clampRange('2026-09', '2026-08', '2026-10').to).toBe('2026-09')
  })

  it('switching kind keeps the place', () => {
    const october = parsePeriod('2026-10')!
    expect(periodKey(switchKind(october, 'range', '2026-10'))).toBe('2026-08..2026-10')
    expect(periodKey(switchKind(october, 'year', '2026-10'))).toBe('2026')
    expect(periodKey(switchKind(parsePeriod('2026')!, 'month', '2026-10'))).toBe('2026-10')
    expect(periodKey(switchKind(parsePeriod('2025')!, 'range', '2026-10'))).toBe('2025-01..2025-12')
  })
})
