import { render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ReadTwiceScene } from './ReadTwiceScene'

const PROPS = {
  figure: '32,100,000',
  aiLabel: 'AI reader',
  witnessLabel: 'Witness',
  caption: 'read twice',
  resultLabel: 'agreed by two readings',
}

afterEach(() => vi.unstubAllGlobals())

describe('ReadTwiceScene (spec 018, AC-018-2)', () => {
  it('shows the figure, both readings, the result and the caption', () => {
    render(<ReadTwiceScene {...PROPS} />)
    expect(screen.getByText('32,100,000')).toBeInTheDocument()
    expect(screen.getByText('AI reader')).toBeInTheDocument()
    expect(screen.getByText('Witness')).toBeInTheDocument()
    expect(screen.getByText(/agreed by two readings/)).toBeInTheDocument()
    expect(screen.getByText('read twice')).toBeInTheDocument()
  })

  it('renders settled when reduced motion is requested', () => {
    vi.stubGlobal('matchMedia', () => ({
      matches: true,
      media: '(prefers-reduced-motion: reduce)',
      addEventListener: () => {},
      removeEventListener: () => {},
    }))
    const { container } = render(<ReadTwiceScene {...PROPS} />)
    expect(container.querySelector('.read-twice')).toHaveAttribute('data-state', 'settled')
    // The meaning never depends on the motion.
    expect(screen.getByText(/agreed by two readings/)).toBeInTheDocument()
  })
})
