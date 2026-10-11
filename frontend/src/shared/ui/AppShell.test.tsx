import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { AppShell } from './AppShell'

// Mock useAuth
vi.mock('../../app/providers/useAuth', () => ({
  useAuth: () => ({
    user: { displayName: 'Maya Sari', email: 'maya@example.com' },
    signOut: vi.fn(),
  }),
}))

describe('AppShell', () => {
  beforeEach(() => {
    // Set default desktop window width
    window.innerWidth = 1440
  })

  it('renders workspace name and navigation on desktop (large screen)', () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <AppShell>
          <div>Dashboard Content</div>
        </AppShell>
      </MemoryRouter>
    )

    expect(screen.getByText('Sunrise Coffee Roasters')).toBeInTheDocument()
    expect(screen.getByText('Dashboard Content')).toBeInTheDocument()
    expect(screen.getByText('Free trial: 23 days left')).toBeInTheDocument()
  })

  it('renders bottom navigation and floating upload button on compact screen', () => {
    window.innerWidth = 390
    window.dispatchEvent(new Event('resize'))

    render(
      <MemoryRouter initialEntries={['/']}>
        <AppShell>
          <div>Mobile View</div>
        </AppShell>
      </MemoryRouter>
    )

    expect(screen.getByLabelText('Mobile navigation')).toBeInTheDocument()
    expect(screen.getByText('Mobile View')).toBeInTheDocument()
  })

  it('renders navigation rail on medium screen', () => {
    window.innerWidth = 834
    window.dispatchEvent(new Event('resize'))

    render(
      <MemoryRouter initialEntries={['/']}>
        <AppShell>
          <div>Tablet View</div>
        </AppShell>
      </MemoryRouter>
    )

    expect(screen.getByLabelText('Rail navigation')).toBeInTheDocument()
    expect(screen.getByText('Tablet View')).toBeInTheDocument()
  })
})
