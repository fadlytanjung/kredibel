import { describe, expect, it } from 'vitest'
import { shiftLeft, short, sumAmounts, unitFor } from './units'

describe('chart amounts (no float ever holds money)', () => {
  it('moves the decimal point in the string', () => {
    expect(shiftLeft('412500000.00', 6)).toBe('412.50000000')
    expect(shiftLeft('-950000', 6)).toBe('-0.950000')
    expect(shiftLeft('12.5', 0)).toBe('12.5')
  })

  it('picks the unit that keeps the largest amount readable', () => {
    expect(unitFor(['1355800000.00', '12.00']).key).toBe('millions')
    expect(unitFor(['250000.00']).key).toBe('thousands')
    expect(unitFor(['4887.94']).key).toBe('units')
  })

  it('prints millions with one decimal, signed when asked', () => {
    const millions = unitFor(['412500000.00'])
    expect(short('412500000.00', millions)).toBe('412.5')
    expect(short('11849999.00', millions, true)).toBe('+11.8')
    expect(short('-36300000.00', millions, true)).toBe('-36.3')
  })

  it('adds exactly, as minor units', () => {
    expect(sumAmounts(['48250000.00', '51900000.00'])).toBe('100150000.00')
    expect(sumAmounts(['0.10', '0.20'])).toBe('0.30')
    expect(sumAmounts(['-1.05', '0.05'])).toBe('-1.00')
    expect(sumAmounts([])).toBe('0.00')
  })
})
