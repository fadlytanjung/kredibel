import { describe, expect, it } from 'vitest'
import { cardPosition, spotBox } from './position'
import { booksPeriod, stepPath, TOUR_STEPS, tourSteps } from './steps'

describe('the guided tour (spec 021, AC-021-4…6)', () => {
  it('walks every menu, runs for owners only, and ends on a card', () => {
    expect(tourSteps('owner').map((s) => s.id)).toEqual(TOUR_STEPS.map((s) => s.id))
    expect(tourSteps('reviewer').map((s) => s.id)).not.toContain('runs')
    expect(tourSteps('owner').at(-1)?.target).toBeUndefined()
  })

  it('opens the dashboard on the months that have books, at most 12', () => {
    expect(booksPeriod(['2026-04', '2026-09', '2026-06'])).toBe('2026-04..2026-09')
    expect(booksPeriod(['2025-01', '2026-09'])).toBe('2025-10..2026-09')
    expect(booksPeriod(['2026-09'])).toBe('2026-09')
    expect(booksPeriod([])).toBeNull()
    expect(stepPath(TOUR_STEPS[1], '2026-04..2026-09')).toBe('/dashboard?period=2026-04..2026-09')
    expect(stepPath(TOUR_STEPS[4], '2026-04..2026-09')).toBe('/documents')
  })

  it('lights the part with room around it and puts the card below, above or at the bottom on phones', () => {
    const view = { width: 1440, height: 900 }
    const spot = spotBox({ top: 100, left: 300, width: 800, height: 200 }, view)
    expect(spot).toEqual({ top: 92, left: 292, width: 816, height: 216 })
    expect(cardPosition(spot, { width: 360, height: 200 }, view)).toEqual({ top: 320, left: 292, placement: 'below' })
    const low = spotBox({ top: 600, left: 1300, width: 120, height: 200 }, view)
    expect(cardPosition(low, { width: 360, height: 200 }, view)).toMatchObject({ placement: 'above', left: 1064 })
    expect(cardPosition(null, { width: 360, height: 200 }, view)).toMatchObject({ placement: 'center', left: 540 })
    expect(cardPosition(spot, { width: 358, height: 220 }, { width: 390, height: 844 })).toEqual({ top: 608, left: 16, placement: 'bottom' })
  })
})
