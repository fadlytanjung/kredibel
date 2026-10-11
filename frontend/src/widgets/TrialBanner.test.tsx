import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { TrialBanner } from './TrialBanner'

const renderBanner = (status: 'TRIALING' | 'TRIAL_EXPIRED', daysLeft: number) =>
  render(
    <MemoryRouter>
      <TrialBanner trial={{ status, daysLeft, pagesUsed: 0, pagesMax: 400 }} />
    </MemoryRouter>,
  )

describe('TrialBanner (AC-013-12)', () => {
  it('stays away while more than 7 days are left', () => {
    renderBanner('TRIALING', 8)
    expect(screen.queryByRole('status')).not.toBeInTheDocument()
  })

  it('says what happens in the last 7 days', () => {
    renderBanner('TRIALING', 3)
    expect(screen.getByRole('status')).toHaveTextContent(
      'Your free trial ends in 3 days. Your books stay readable after that; new uploads pause.',
    )
  })

  it('says the trial ended and the books stay readable', () => {
    renderBanner('TRIAL_EXPIRED', 0)
    expect(screen.getByRole('status')).toHaveTextContent(
      'Your trial has ended. Your books stay readable; new uploads are paused.',
    )
  })
})
