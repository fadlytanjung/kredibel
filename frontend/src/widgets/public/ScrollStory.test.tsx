import { act, render, screen, within } from '@testing-library/react'
import type { MotionValue } from 'motion/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { REDUCED, stubMedia } from '../../shared/lib/sceneTestUtils'
import { ScrollStory } from './ScrollStory'

// jsdom cannot scroll, so the test drives the scroll progress value itself.
const scroll = vi.hoisted(() => ({ progress: null as MotionValue<number> | null }))

vi.mock('motion/react', async (importOriginal) => {
  const actual = await importOriginal<typeof import('motion/react')>()
  scroll.progress = actual.motionValue(0)
  return {
    ...actual,
    useScroll: () => ({
      scrollX: actual.motionValue(0),
      scrollY: actual.motionValue(0),
      scrollXProgress: actual.motionValue(0),
      scrollYProgress: scroll.progress,
    }),
  }
})

const CHAPTERS = [
  { key: 'a', title: 'Arrives in any order', body: 'Body a' },
  { key: 'b', title: 'Read twice', body: 'Body b', extra: <button type="button">Inspect</button> },
  { key: 'c', title: 'Checked', body: 'Body c' },
  { key: 'd', title: 'Reconciled', body: 'Body d' },
]

function renderStory() {
  return render(
    <ScrollStory
      eyebrow="Inside the reading room"
      title="Watch one month get checked."
      lead="Lead"
      chapters={CHAPTERS}
      stage={<div data-testid="stage-piece" />}
    />,
  )
}

afterEach(() => {
  vi.unstubAllGlobals()
  act(() => scroll.progress?.set(0))
})

describe('ScrollStory (spec 020, AC-020-4, AC-020-12)', () => {
  it('renders one DOM: the heading, then every chapter as a heading, in order', () => {
    stubMedia({})
    renderStory()
    expect(screen.getByRole('heading', { level: 2, name: 'Watch one month get checked.' })).toBeInTheDocument()
    const titles = screen.getAllByRole('heading', { level: 3 }).map((h) => h.textContent)
    expect(titles).toEqual(['Arrives in any order', 'Read twice', 'Checked', 'Reconciled'])
    // Interactive content stays in the chapter, outside the decorative stage.
    expect(screen.getByRole('button', { name: 'Inspect' }).closest('[aria-hidden="true"]')).toBeNull()
  })

  it('keeps the 3D stage away from assistive technology', () => {
    stubMedia({})
    renderStory()
    expect(screen.getByTestId('stage-piece').closest('[aria-hidden="true"]')).not.toBeNull()
  })

  it('marks the chapter the scroll is in', () => {
    stubMedia({})
    const { container } = renderStory()
    const story = container.querySelector('section')!
    expect(story).toHaveAttribute('data-chapter', '0')
    act(() => scroll.progress?.set(0.55))
    expect(story).toHaveAttribute('data-chapter', '2')
    const chapters = within(story).getAllByRole('listitem').filter((li) => li.classList.contains('pub-chapter'))
    expect(chapters.map((li) => li.getAttribute('data-active'))).toEqual(['false', 'false', 'true', 'false'])
  })

  it('stays settled under reduced motion', () => {
    stubMedia({ [REDUCED]: true })
    const { container } = renderStory()
    act(() => scroll.progress?.set(0.9))
    expect(container.querySelector('section')).toHaveAttribute('data-chapter', '0')
  })
})
