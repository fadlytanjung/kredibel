import { act, render, screen } from '@testing-library/react'
import type { MotionValue } from 'motion/react'
import { useRef } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { REDUCED, stubMedia } from './sceneTestUtils'
import { useScrollProgress } from './useScrollProgress'

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

function Probe({ chapters }: { chapters?: number }) {
  const ref = useRef<HTMLDivElement>(null)
  const chapter = useScrollProgress(ref, { chapters })
  return <div ref={ref} data-testid="probe" data-chapter={chapter} />
}

afterEach(() => {
  vi.unstubAllGlobals()
  act(() => scroll.progress?.set(0))
})

describe('useScrollProgress (spec 020, AC-020-12)', () => {
  it('writes the progress as --p on the element', () => {
    stubMedia({})
    render(<Probe />)
    act(() => scroll.progress?.set(0.25))
    expect(screen.getByTestId('probe').style.getPropertyValue('--p')).toBe('0.2500')
  })

  it('names the chapter the progress is in', () => {
    stubMedia({})
    render(<Probe chapters={4} />)
    const probe = screen.getByTestId('probe')
    expect(probe).toHaveAttribute('data-chapter', '0')
    act(() => scroll.progress?.set(0.6))
    expect(probe).toHaveAttribute('data-chapter', '2')
    act(() => scroll.progress?.set(1))
    expect(probe).toHaveAttribute('data-chapter', '3')
  })

  it('writes nothing under reduced motion', () => {
    stubMedia({ [REDUCED]: true })
    render(<Probe chapters={4} />)
    act(() => scroll.progress?.set(0.6))
    const probe = screen.getByTestId('probe')
    expect(probe.style.getPropertyValue('--p')).toBe('')
    expect(probe).toHaveAttribute('data-chapter', '0')
  })
})
