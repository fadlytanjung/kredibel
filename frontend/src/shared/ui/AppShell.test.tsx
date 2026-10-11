import { fireEvent, render, screen, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AppShell, type AppShellProps } from './AppShell'

function setWidth(width: number) {
  window.innerWidth = width
  window.dispatchEvent(new Event('resize'))
}

function renderShell(props: Partial<AppShellProps> = {}, path = '/') {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <AppShell {...props}>
        <div>Page content</div>
      </AppShell>
    </MemoryRouter>,
  )
}

const FULL_PROPS: Partial<AppShellProps> = {
  user: { name: 'Demo Owner', role: 'owner' },
  workspace: { name: 'Synthetic Books Ltd', subtitle: 'COMPANY · IDR · IFRS' },
  trial: { daysLeft: 23, pagesUsed: 286, pagesMax: 400 },
  counts: { documents: 12, review: 3, risk: 1 },
}

describe('AppShell (AC-001-16)', () => {
  beforeEach(() => setWidth(1440))

  it('shows the docs/11 navigation, workspace, trial and Upload from 1200 px', () => {
    renderShell(FULL_PROPS)

    const nav = screen.getByRole('navigation', { name: 'Main navigation' })
    for (const label of [
      'Dashboard',
      'Documents',
      'Reconciliation',
      'Review',
      'Risk',
      'Clients and suppliers',
      'Assistant',
    ]) {
      expect(within(nav).getByText(label)).toBeInTheDocument()
    }
    expect(screen.getByText('Settings')).toBeInTheDocument()
    expect(screen.getByText('Synthetic Books Ltd')).toBeInTheDocument()
    expect(screen.getByText('Free trial: 23 days left')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Upload' })).toBeInTheDocument()
    expect(screen.getByText('Page content')).toBeInTheDocument()
  })

  it('invents nothing when the caller has no workspace data yet', () => {
    renderShell({ user: { name: 'Demo Owner', role: 'owner' } })

    expect(screen.queryByText(/Free trial/)).not.toBeInTheDocument()
    expect(screen.queryByText('Sunrise Coffee Roasters')).not.toBeInTheDocument()
    expect(screen.getByRole('navigation', { name: 'Main navigation' })).toBeInTheDocument()
  })

  it('signs out through the callback it was given', () => {
    const onSignOut = vi.fn()
    renderShell({ ...FULL_PROPS, onSignOut })

    fireEvent.click(screen.getByRole('button', { name: 'Sign out' }))
    expect(onSignOut).toHaveBeenCalledOnce()
  })

  it('shows the rail with short labels from 600 to 1199 px', () => {
    setWidth(834)
    renderShell(FULL_PROPS)

    expect(screen.getByLabelText('Rail navigation')).toBeInTheDocument()
    expect(screen.getByText('Reconcile')).toBeInTheDocument()
  })

  it('shows the bottom navigation and the More sheet below 600 px; Esc closes the sheet', () => {
    setWidth(390)
    renderShell(FULL_PROPS)

    const bottom = screen.getByRole('navigation', { name: 'Mobile navigation' })
    for (const label of ['Dashboard', 'Docs', 'Review', 'Risk', 'More']) {
      expect(within(bottom).getByText(label)).toBeInTheDocument()
    }

    fireEvent.click(within(bottom).getByText('More'))
    const sheet = screen.getByRole('dialog')
    for (const label of ['Reconciliation', 'Clients and suppliers', 'Assistant', 'Settings']) {
      expect(within(sheet).getByText(label)).toBeInTheDocument()
    }

    fireEvent.keyDown(window, { key: 'Escape' })
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })
})
