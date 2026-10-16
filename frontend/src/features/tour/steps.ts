/**
 * The guided tour's steps (spec 021, AC-021-4): one per menu, each opening its page and lighting
 * one part of it. A step without a part, or whose part is not on the page, shows its card alone.
 */

export interface TourStep {
  id: string
  /** The page to open; dashboard steps open the months that have books when given. */
  path: string
  /** The part of the page to light (a CSS selector), if any. */
  target?: string
  ownerOnly?: boolean
}

export const TOUR_STEPS: TourStep[] = [
  { id: 'welcome', path: '/dashboard' },
  { id: 'period', path: '/dashboard', target: '#content .dash-period' },
  { id: 'figures', path: '/dashboard', target: '#content .dash .ledger' },
  { id: 'flow', path: '/dashboard', target: '#content .charts' },
  { id: 'upload', path: '/documents', target: '#content .tray' },
  { id: 'months', path: '/months/all', target: '#content .table-panel' },
  { id: 'review', path: '/review', target: '#content .table-panel' },
  { id: 'risk', path: '/risk', target: '#content .find-group' },
  { id: 'labels', path: '/labels', target: '#content .table-panel' },
  { id: 'runs', path: '/runs', target: '#content .table-panel', ownerOnly: true },
  { id: 'assistant', path: '/assistant', target: '#content .composer' },
  { id: 'done', path: '/dashboard' },
]

export function tourSteps(role: string | null | undefined): TourStep[] {
  return TOUR_STEPS.filter((step) => !step.ownerOnly || role === 'owner')
}

/** The dashboard period that shows the books: the last up to 12 months that have any. */
export function booksPeriod(monthsWithBooks: string[]): string | null {
  const months = [...new Set(monthsWithBooks)].sort()
  if (months.length === 0) return null
  const last = months[months.length - 1]
  const [year, month] = last.split('-').map(Number)
  const firstIndex = Math.max(year * 12 + month - 1 - 11, Number(months[0].slice(0, 4)) * 12 + Number(months[0].slice(5, 7)) - 1)
  const first = `${String(Math.floor(firstIndex / 12)).padStart(4, '0')}-${String((firstIndex % 12) + 1).padStart(2, '0')}`
  return first === last ? last : `${first}..${last}`
}

/** Where a step goes: its page, with the books' period on the dashboard. */
export function stepPath(step: TourStep, period: string | null): string {
  return step.path === '/dashboard' && period ? `/dashboard?period=${period}` : step.path
}
