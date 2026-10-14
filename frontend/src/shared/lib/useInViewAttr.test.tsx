import { act, render, screen } from '@testing-library/react'
import { useRef } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { REDUCED, stubMedia } from './sceneTestUtils'
import { useInViewAttr } from './useInViewAttr'

function Probe({ once }: { once?: boolean }) {
  const ref = useRef<HTMLDivElement>(null)
  return <div ref={ref} data-testid="probe" {...useInViewAttr(ref, { once })} />
}

type Callback = (entries: Partial<IntersectionObserverEntry>[]) => void

function stubObserver() {
  const observers: { cb: Callback; disconnect: ReturnType<typeof vi.fn> }[] = []
  class FakeObserver {
    disconnect = vi.fn()
    observe = vi.fn()
    unobserve = vi.fn()
    constructor(cb: Callback) {
      observers.push({ cb, disconnect: this.disconnect })
    }
  }
  vi.stubGlobal('IntersectionObserver', FakeObserver)
  return {
    observers,
    fire: (isIntersecting: boolean) => act(() => observers.forEach((o) => o.cb([{ isIntersecting }]))),
  }
}

afterEach(() => vi.unstubAllGlobals())

describe('useInViewAttr (spec 018, AC-018-12)', () => {
  it('counts as in view when the browser has no IntersectionObserver', () => {
    stubMedia({})
    vi.stubGlobal('IntersectionObserver', undefined)
    render(<Probe />)
    expect(screen.getByTestId('probe')).toHaveAttribute('data-inview', 'true')
  })

  it('turns on when the element enters the viewport, and stays on by default', () => {
    stubMedia({})
    const { fire, observers } = stubObserver()
    render(<Probe />)
    const probe = screen.getByTestId('probe')
    expect(probe).toHaveAttribute('data-inview', 'false')
    fire(true)
    expect(probe).toHaveAttribute('data-inview', 'true')
    expect(observers[0].disconnect).toHaveBeenCalled()
    fire(false)
    expect(probe).toHaveAttribute('data-inview', 'true')
  })

  it('follows the element out again when once is false', () => {
    stubMedia({})
    const { fire } = stubObserver()
    render(<Probe once={false} />)
    fire(true)
    fire(false)
    expect(screen.getByTestId('probe')).toHaveAttribute('data-inview', 'false')
  })

  it('shows everything at once under reduced motion, without observing', () => {
    stubMedia({ [REDUCED]: true })
    const { observers } = stubObserver()
    render(<Probe />)
    expect(screen.getByTestId('probe')).toHaveAttribute('data-inview', 'true')
    expect(observers).toHaveLength(0)
  })
})
