import { describe, it, expect } from 'vitest'
import { getSizeClass } from './useSizeClass'

describe('getSizeClass', () => {
  it('identifies compact below 600px', () => {
    expect(getSizeClass(360)).toBe('compact')
    expect(getSizeClass(390)).toBe('compact')
    expect(getSizeClass(599)).toBe('compact')
  })

  it('identifies medium between 600px and 839px', () => {
    expect(getSizeClass(600)).toBe('medium')
    expect(getSizeClass(834)).toBe('medium')
    expect(getSizeClass(839)).toBe('medium')
  })

  it('identifies expanded between 840px and 1199px', () => {
    expect(getSizeClass(840)).toBe('expanded')
    expect(getSizeClass(1024)).toBe('expanded')
    expect(getSizeClass(1199)).toBe('expanded')
  })

  it('identifies large between 1200px and 1599px', () => {
    expect(getSizeClass(1200)).toBe('large')
    expect(getSizeClass(1440)).toBe('large')
    expect(getSizeClass(1599)).toBe('large')
  })

  it('identifies wide from 1600px up', () => {
    expect(getSizeClass(1600)).toBe('wide')
    expect(getSizeClass(1920)).toBe('wide')
  })
})
