import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { ProgressLine } from './ProgressLine'

describe('ProgressLine (AC-004-8)', () => {
  it('renders reading page progress with progressbar attributes and percentage', () => {
    render(<ProgressLine current={3} total={18} status="running" />)

    expect(screen.getByText('Reading page 3 of 18')).toBeInTheDocument()
    expect(screen.getByText('17%')).toBeInTheDocument()

    const progressBar = screen.getByRole('progressbar')
    expect(progressBar).toHaveAttribute('aria-valuenow', '17')
    expect(progressBar).toHaveAttribute('aria-valuemin', '0')
    expect(progressBar).toHaveAttribute('aria-valuemax', '100')
  })

  it('renders month states with appropriate badges', () => {
    const { rerender } = render(<ProgressLine monthState="COLLECTING" />)
    expect(screen.getByText('Collecting')).toBeInTheDocument()

    rerender(<ProgressLine monthState="RECONCILING" />)
    expect(screen.getByText('Reconciling')).toBeInTheDocument()

    rerender(<ProgressLine monthState="RECONCILED" />)
    expect(screen.getByText('Reconciled')).toBeInTheDocument()

    rerender(<ProgressLine monthState="NEEDS_REVIEW" />)
    expect(screen.getByText('Needs review')).toBeInTheDocument()
  })

  it('renders paused reconciliation note when daily quota is exceeded', () => {
    render(
      <ProgressLine
        monthState="COLLECTING"
        note="Reconciliation paused until tomorrow (daily limit)"
      />,
    )

    expect(
      screen.getByText('Reconciliation paused until tomorrow (daily limit)'),
    ).toBeInTheDocument()
  })

  it('renders custom label and status', () => {
    render(<ProgressLine label="Processing ledger export..." status="done" />)

    expect(screen.getByText('Processing ledger export...')).toBeInTheDocument()
  })
})
