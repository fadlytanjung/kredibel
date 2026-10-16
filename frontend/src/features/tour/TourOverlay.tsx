/**
 * One step of the guided tour (spec 021, AC-021-4, AC-021-6): the page is dimmed except for the
 * lit part, and a card says what it is, with Back, Next and Skip. The card is a labelled dialog
 * that keeps the focus; arrows move, Esc ends. Without a part (or before it appears) the card is
 * centred, or at the bottom on phones.
 */

import { type KeyboardEvent, useEffect, useLayoutEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Icon } from '../../shared/ui'
import { type Box, COMPACT_BELOW, cardPosition, spotBox } from './position'
import type { TourStep } from './steps'

const FIND_FOR_MS = 6000 // a page opened by the step may still be loading its chunk and data
const REMEASURE_MS = 400 // charts and tables settle after their data arrives
const TOP_ROOM = 72 // the phone's top bar

function viewport() {
  return { width: window.innerWidth, height: window.innerHeight }
}

export function TourOverlay({
  step,
  index,
  total,
  workspaceName,
  onBack,
  onNext,
  onStop,
}: {
  step: TourStep
  index: number
  total: number
  workspaceName?: string
  onBack: () => void
  onNext: () => void
  onStop: () => void
}) {
  const { t } = useTranslation('tour')
  const card = useRef<HTMLElement>(null)
  const heading = useRef<HTMLHeadingElement>(null)
  const [spot, setSpot] = useState<Box | null>(null)
  const [place, setPlace] = useState<{ top: number; left: number } | null>(null)
  const last = index + 1 >= total

  // Find the part (pages load after the step opens them), bring it into view, and follow it.
  useEffect(() => {
    if (!step.target) return
    const selector = step.target
    let frame = 0
    let found: Element | null = null
    const began = performance.now()
    const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
    // On phones the card sits at the bottom, so the part goes to the top, below the top bar.
    const show = (el: Element, smooth: boolean) => {
      const behavior = smooth && !reduce ? 'smooth' : 'auto'
      if (window.innerWidth < COMPACT_BELOW) {
        window.scrollTo({ top: window.scrollY + el.getBoundingClientRect().top - TOP_ROOM, behavior })
      } else {
        el.scrollIntoView({ block: 'center', behavior })
      }
    }
    // A page may redraw the part (its data reloads): find it again, show it, follow layout changes.
    const measure = () => {
      if (!found || !found.isConnected) {
        const again = document.querySelector(selector)
        if (again && again !== found) show(again, false)
        found = again
      }
      if (found) setSpot(spotBox(found.getBoundingClientRect(), viewport()))
    }
    const look = () => {
      found = document.querySelector(selector)
      if (found) {
        show(found, true)
        measure()
        return
      }
      if (performance.now() - began < FIND_FOR_MS) frame = requestAnimationFrame(look)
    }
    frame = requestAnimationFrame(look)
    const follow = () => {
      cancelAnimationFrame(frame)
      frame = requestAnimationFrame(measure)
    }
    window.addEventListener('scroll', follow, true)
    window.addEventListener('resize', follow)
    const settle = window.setInterval(follow, REMEASURE_MS)
    return () => {
      window.clearInterval(settle)
      cancelAnimationFrame(frame)
      window.removeEventListener('scroll', follow, true)
      window.removeEventListener('resize', follow)
    }
  }, [step.target])

  // Place the card once its size is known, and again whenever the light moves.
  useLayoutEffect(() => {
    const box = card.current?.getBoundingClientRect()
    if (!box) return
    const next = cardPosition(spot, { width: box.width, height: box.height }, viewport())
    setPlace({ top: next.top, left: next.left })
  }, [spot])

  // The heading takes the focus once the card is placed (a hidden card cannot), so each step is read.
  const placed = place !== null
  useEffect(() => {
    if (placed) heading.current?.focus()
  }, [placed])

  // Esc and the arrows work wherever the focus is while the tour is open.
  useEffect(() => {
    const onKey = (e: globalThis.KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault()
        onStop()
      } else if (e.key === 'ArrowRight') {
        e.preventDefault()
        onNext()
      } else if (e.key === 'ArrowLeft' && index > 0) {
        e.preventDefault()
        onBack()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [index, onBack, onNext, onStop])

  const onKeyDown = (e: KeyboardEvent<HTMLElement>) => {
    if (e.key === 'Tab') {
      // The focus stays in the card while the tour is open.
      const items = card.current?.querySelectorAll<HTMLElement>('button:not([disabled])')
      if (!items || items.length === 0) return
      const first = items[0]
      const lastItem = items[items.length - 1]
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault()
        lastItem.focus()
      } else if (!e.shiftKey && document.activeElement === lastItem) {
        e.preventDefault()
        first.focus()
      }
    }
  }

  return (
    <div className={`tour${spot ? '' : ' no-spot'}`}>
      <div className="tour-catch" aria-hidden="true" />
      {spot && (
        <div
          className="tour-spot"
          aria-hidden="true"
          style={{ top: spot.top, left: spot.left, width: spot.width, height: spot.height }} /* allow-raw-style: the lit part's box, measured */
        />
      )}
      <section
        ref={card}
        className={`tour-card${place ? '' : ' is-measuring'}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby="tour-h"
        aria-describedby="tour-p"
        onKeyDown={onKeyDown}
        style={place ? { top: place.top, left: place.left } : undefined} /* allow-raw-style: the card beside the lit part */
      >
        <p className="tour-step">{t('stepOf', { n: index + 1, total })}</p>
        <h2 id="tour-h" ref={heading} tabIndex={-1}>
          {t(`steps.${step.id}.title`, { name: workspaceName || t('yourWorkspace') })}
        </h2>
        <p id="tour-p">{t(`steps.${step.id}.body`)}</p>
        <div className="tour-actions">
          {!last && (
            <button type="button" className="button button-quiet button-sm" onClick={onStop}>
              {t('skip')}
            </button>
          )}
          <span className="tour-grow" />
          {index > 0 && (
            <button type="button" className="button button-secondary button-sm" onClick={onBack}>
              <Icon name="chevron-left" size="sm" />
              {t('back')}
            </button>
          )}
          <button type="button" className="button button-primary button-sm" onClick={onNext}>
            {t(last ? 'done' : 'next')}
            {!last && <Icon name="chevron-right" size="sm" />}
          </button>
        </div>
      </section>
    </div>
  )
}
