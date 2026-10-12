import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { SeverityBadge } from './SeverityBadge'

describe('SeverityBadge (spec 008, AC-008-10, NFR-08)', () => {
  it('renders colour class, icon, and text for CRITICAL', () => {
    const { container } = render(<SeverityBadge severity="CRITICAL" />)
    const badge = screen.getByText('Critical')
    expect(badge).toBeInTheDocument()
    expect(badge.closest('.badge-critical')).toBeInTheDocument()
    // Icon is rendered inside badge
    const svg = container.querySelector('svg')
    expect(svg).toBeInTheDocument()
  })

  it('renders colour class, icon, and text for HIGH', () => {
    const { container } = render(<SeverityBadge severity="HIGH" />)
    const badge = screen.getByText('High')
    expect(badge).toBeInTheDocument()
    expect(badge.closest('.badge-high')).toBeInTheDocument()
    expect(container.querySelector('svg')).toBeInTheDocument()
  })

  it('renders colour class, icon, and text for MEDIUM', () => {
    const { container } = render(<SeverityBadge severity="MEDIUM" />)
    const badge = screen.getByText('Medium')
    expect(badge).toBeInTheDocument()
    expect(badge.closest('.badge-medium')).toBeInTheDocument()
    expect(container.querySelector('svg')).toBeInTheDocument()
  })

  it('renders colour class, icon, and text for LOW', () => {
    const { container } = render(<SeverityBadge severity="LOW" />)
    const badge = screen.getByText('Low')
    expect(badge).toBeInTheDocument()
    expect(badge.closest('.badge-low')).toBeInTheDocument()
    expect(container.querySelector('svg')).toBeInTheDocument()
  })
})
