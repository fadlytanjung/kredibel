/** Where the tour's light and card go (spec 021, AC-021-6). Pure: rectangles in, rectangles out. */

export interface Box {
  top: number
  left: number
  width: number
  height: number
}

export const SPOT_PADDING = 8
export const GAP = 12
export const EDGE = 16
export const COMPACT_BELOW = 600

/** The light around the part: the part's box with room around it, inside the viewport. */
export function spotBox(target: Box, viewport: { width: number; height: number }): Box {
  const top = Math.max(target.top - SPOT_PADDING, 0)
  const left = Math.max(target.left - SPOT_PADDING, 0)
  const bottom = Math.min(target.top + target.height + SPOT_PADDING, viewport.height)
  const right = Math.min(target.left + target.width + SPOT_PADDING, viewport.width)
  return { top, left, width: Math.max(right - left, 0), height: Math.max(bottom - top, 0) }
}

/**
 * The card: on phones at the bottom; elsewhere below the light when it fits, else above it, else
 * over the light's lower part; aligned with the light's left edge and kept inside the viewport.
 * Without a light it is centred.
 */
export function cardPosition(
  spot: Box | null,
  card: { width: number; height: number },
  viewport: { width: number; height: number },
): { top: number; left: number; placement: 'below' | 'above' | 'over' | 'center' | 'bottom' } {
  if (viewport.width < COMPACT_BELOW) {
    return { top: viewport.height - card.height - EDGE, left: EDGE, placement: 'bottom' }
  }
  const clampLeft = (left: number) => Math.min(Math.max(left, EDGE), viewport.width - card.width - EDGE)
  if (!spot) {
    return { top: Math.max((viewport.height - card.height) / 2, EDGE), left: clampLeft((viewport.width - card.width) / 2), placement: 'center' }
  }
  const below = spot.top + spot.height + GAP
  if (below + card.height + EDGE <= viewport.height) return { top: below, left: clampLeft(spot.left), placement: 'below' }
  const above = spot.top - GAP - card.height
  if (above >= EDGE) return { top: above, left: clampLeft(spot.left), placement: 'above' }
  return { top: Math.max(viewport.height - card.height - EDGE, EDGE), left: clampLeft(spot.left), placement: 'over' }
}
