import { describe, expect, it } from 'vitest'
import { sumDecimals } from './decimal'

describe('sumDecimals', () => {
  it('adds money exactly, where floats would drift', () => {
    expect(sumDecimals(['0.10', '0.20'])).toBe('0.30')
    expect(sumDecimals(['-12.40', '250.00'])).toBe('237.60')
    expect(sumDecimals(['-250.00', '12.40'])).toBe('-237.60')
  })

  it('keeps every digit of large amounts and the finest scale', () => {
    expect(sumDecimals(['12345678901234567.89', '0.11'])).toBe('12345678901234568.00')
    expect(sumDecimals(['1.005', '2'])).toBe('3.005')
  })

  it('is zero for nothing and skips what is not a decimal', () => {
    expect(sumDecimals([])).toBe('0.00')
    expect(sumDecimals(['abc', '5.00'])).toBe('5.00')
  })
})
