/**
 * The shell's structure and behaviour (AC-001-16, AC-013-12). Which parts show at which width is
 * kit.css's container queries (ADR-019) and is covered by the visual tests at 390/834/1440 px.
 */

import { fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { AppShell, type AppShellProps } from './AppShell'

function renderShell(props: Partial<AppShellProps> = {}, path = '/dashboard') {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AppShell {...props}>
        <div>Page content</div>
      </AppShell>
    </MemoryRouter>,
  )
}

const FULL_PROPS: Partial<AppShellProps> = {
  user: { name: 'Maya Sari', role: 'owner' },
  workspace: { name: 'Synthetic Books Ltd', subtitle: 'Company, IDR, IFRS' },
  trial: { status: 'TRIALING', daysLeft: 23, pagesUsed: 286, pagesMax: 400 },
  counts: { documents: 92, review: 9, risk: 2, labels: 37 },
}

describe('AppShell (AC-001-16)', () => {
  it('has the navigation of the mocks', () => {
    renderShell(FULL_PROPS)
    const main = screen.getByRole('navigation', { name: 'Main' })
    const titles = within(main).getAllByRole('link').map((link) => link.getAttribute('title'))
    expect(titles).toEqual([
      'Dashboard', 'Documents', 'Reconciliation', 'Review', 'Risk',
      'Assistant', 'Labels', 'Runs',
    ])
    // Clients and suppliers are not in the menus (16 Oct 2026); the pages stay for links.
    expect(within(main).queryByRole('link', { name: /Clients/ })).toBeNull()
  })

  it('shows the workspace, trial status and profile it was given, and invents nothing', () => {
    renderShell(FULL_PROPS)
    expect(screen.getByText('Synthetic Books Ltd')).toBeInTheDocument()
    const trial = screen.getByRole('link', { name: /Free trial: 23 days left/ })
    expect(trial).toHaveAttribute('href', '/settings/plan')
    expect(trial).toHaveTextContent('286 of 400 pages')
    expect(screen.getByRole('link', { name: 'Settings, signed in as Maya Sari (Owner)' })).toHaveTextContent('MS')
  })

  it('opens Settings from the profile row; there is no separate Settings item', () => {
    renderShell(FULL_PROPS, '/settings/plan')
    const profile = screen.getByRole('link', { name: /^Settings, signed in as Maya Sari/ })
    expect(profile).toHaveAttribute('href', '/settings/profile')
    expect(profile).toHaveAttribute('aria-current', 'page')
    expect(screen.queryByRole('navigation', { name: 'Settings' })).not.toBeInTheDocument()
  })

  it('says when the trial has ended in the sidebar (AC-013-12)', () => {
    renderShell({ ...FULL_PROPS, trial: { status: 'TRIAL_EXPIRED', daysLeft: 0, pagesUsed: 12, pagesMax: 400 } })
    expect(screen.getByRole('link', { name: /Your free trial has ended/ })).toHaveTextContent('12 of 400 pages')
  })

  it('opens the More sheet from the bottom navigation and closes it with Esc', () => {
    renderShell(FULL_PROPS)
    const bottom = screen.getByRole('navigation', { name: 'Mobile navigation' })
    fireEvent.click(within(bottom).getByRole('button', { name: 'More' }))
    expect(within(screen.getByRole('dialog', { name: 'More' })).getByText('Labels')).toBeInTheDocument()
    fireEvent.keyDown(window, { key: 'Escape' })
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('disables Upload with the reason after the trial (AC-013-12)', () => {
    renderShell({
      ...FULL_PROPS,
      trial: { status: 'TRIAL_EXPIRED', daysLeft: 0, pagesUsed: 0, pagesMax: 400 },
      uploadBlockedReason: 'Uploads are paused because the free trial has ended.',
    })
    const [upload] = screen.getAllByRole('button', { name: 'Upload' })
    expect(upload).toBeDisabled()
    expect(screen.getByText('Trial ended')).toBeInTheDocument()
  })
})
