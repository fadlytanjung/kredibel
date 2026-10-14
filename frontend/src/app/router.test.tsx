import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { AuthContext, type AuthContextType } from '../entities/session'
import { IndexRoute } from './router'

function makeAuth(overrides: Partial<AuthContextType> = {}): AuthContextType {
  return {
    user: null,
    me: null,
    loading: false,
    meError: false,
    needsWorkspace: false,
    signInWithEmail: async () => {},
    signInWithGoogle: async () => {},
    signOut: async () => {},
    refreshMe: async () => {},
    refreshSession: async () => null,
    ...overrides,
  } as AuthContextType
}

function renderIndex(auth: AuthContextType) {
  return render(
    <AuthContext.Provider value={auth}>
      <MemoryRouter initialEntries={['/']}>
        <Routes>
          <Route path="/" element={<IndexRoute />} />
          <Route path="/dashboard" element={<h1>Dashboard</h1>} />
        </Routes>
      </MemoryRouter>
    </AuthContext.Provider>,
  )
}

describe('IndexRoute (spec 018, AC-018-1/9)', () => {
  it('shows the landing for a visitor', () => {
    renderIndex(makeAuth())
    expect(screen.getByRole('heading', { level: 1, name: /Every number has a source/i })).toBeInTheDocument()
  })

  it('redirects a signed-in user to the dashboard', () => {
    const user = { email: 'owner@example.com' } as unknown as AuthContextType['user']
    renderIndex(makeAuth({ user }))
    expect(screen.getByRole('heading', { name: 'Dashboard' })).toBeInTheDocument()
  })

  it('waits while the session is loading', () => {
    renderIndex(makeAuth({ loading: true }))
    expect(screen.getByRole('status')).toHaveTextContent(/Loading/i)
  })
})
