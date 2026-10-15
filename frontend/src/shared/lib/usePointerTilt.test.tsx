import { fireEvent, render, screen } from '@testing-library/react'
import { useRef } from 'react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { FINE_POINTER, REDUCED, stubMedia } from './sceneTestUtils'
import { usePointerTilt } from './usePointerTilt'

function Probe() {
  const ref = useRef<HTMLDivElement>(null)
  usePointerTilt(ref)
  return <div ref={ref} data-testid="probe" />
}

function renderProbe() {
  render(<Probe />)
  const probe = screen.getByTestId('probe')
  probe.getBoundingClientRect = () =>
    ({ left: 0, top: 0, width: 200, height: 100, right: 200, bottom: 100, x: 0, y: 0 }) as DOMRect
  return probe
}

afterEach(() => vi.unstubAllGlobals())

describe('usePointerTilt (spec 020, AC-020-12)', () => {
  it('follows a fine pointer: the lamp position and the pointer flag', () => {
    stubMedia({ [FINE_POINTER]: true })
    const probe = renderProbe()
    fireEvent.pointerMove(probe, { clientX: 150, clientY: 25 })
    expect(probe.style.getPropertyValue('--lx')).toBe('75.00%')
    expect(probe.style.getPropertyValue('--ly')).toBe('25.00%')
    expect(probe).toHaveAttribute('data-pointer', 'on')
    fireEvent.pointerLeave(probe)
    expect(probe).not.toHaveAttribute('data-pointer')
  })

  it('ignores a coarse pointer (touch)', () => {
    stubMedia({ [FINE_POINTER]: false })
    const probe = renderProbe()
    fireEvent.pointerMove(probe, { clientX: 150, clientY: 25 })
    expect(probe.style.getPropertyValue('--lx')).toBe('')
    expect(probe).not.toHaveAttribute('data-pointer')
  })

  it('stays still under reduced motion', () => {
    stubMedia({ [FINE_POINTER]: true, [REDUCED]: true })
    const probe = renderProbe()
    fireEvent.pointerMove(probe, { clientX: 150, clientY: 25 })
    expect(probe.style.getPropertyValue('--lx')).toBe('')
  })
})
